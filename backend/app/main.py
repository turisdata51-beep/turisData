"""Punto de entrada de la API: uvicorn app.main:app --port 8000"""
import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import text

from . import rutas_admin, rutas_publicas
from .calculo import recalcular
from .config import CORS_ORIGENES
from .db import fila, transaccion
from .diccionario import sincronizar
from .seguridad import (auditar, crear_token, hash_contrasena, ip_cliente, usuario_actual,
                        verificar_contrasena)


def _crear_admin_inicial():
    """Si no hay administradores, crea uno con ADMIN_CORREO / ADMIN_CONTRASENA del .env."""
    if fila("SELECT 1 FROM operativo.usuario WHERE rol = 'administrador'"):
        return
    correo, contrasena = os.environ.get("ADMIN_CORREO"), os.environ.get("ADMIN_CONTRASENA")
    if not correo or not contrasena:
        return
    with transaccion() as con:
        con.execute(text("""INSERT INTO operativo.usuario (correo, nombre, hash_contrasena, rol)
                            VALUES (:c, 'Administrador', :h, 'administrador')"""),
                    dict(c=correo.lower(), h=hash_contrasena(contrasena)))


@asynccontextmanager
async def inicio(app: FastAPI):
    if sincronizar():
        recalcular()
    _crear_admin_inicial()
    yield


app = FastAPI(title="Observatorio Turístico Inteligente de Cuenca", version="0.1.0", lifespan=inicio)
app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGENES, allow_methods=["*"], allow_headers=["*"])
app.include_router(rutas_publicas.router)
app.include_router(rutas_admin.router)


class Credenciales(BaseModel):
    correo: str
    contrasena: str


@app.post("/api/auth/login", tags=["auth"])
def login(datos: Credenciales, request: Request):
    usuario = fila("SELECT id, rol, hash_contrasena, activo FROM operativo.usuario WHERE correo = :c",
                   c=datos.correo.strip().lower())
    if not usuario or not usuario["activo"] or not verificar_contrasena(datos.contrasena, usuario["hash_contrasena"]):
        auditar(usuario["id"] if usuario else None, "login", resultado="denegado",
                detalle={"correo": datos.correo, "ip": ip_cliente(request)})
        raise HTTPException(401, "Correo o contraseña incorrectos")
    with transaccion() as con:
        con.execute(text("UPDATE operativo.usuario SET ultimo_acceso = now() WHERE id = :id"), dict(id=usuario["id"]))
    auditar(usuario["id"], "login", detalle={"ip": ip_cliente(request)})
    return {"token": crear_token(usuario)}


@app.get("/api/auth/yo", tags=["auth"])
def yo(u=Depends(usuario_actual)):
    return u


@app.get("/api/salud", tags=["sistema"])
def salud():
    return {"estado": "ok"}
