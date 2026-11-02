"""Punto de entrada de la API (carpeta backend): uvicorn app.main:app --port 8000"""
import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from .api import admin, auth, publico
from .nucleo.config import CORS_ORIGENES
from .nucleo.db import fila, transaccion
from .nucleo.seguridad import hash_contrasena
from .servicios import programador
from .servicios.diccionario import sincronizar
from .servicios.indicadores import recalcular


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
    if sincronizar():  # hay versiones nuevas en el diccionario de indicadores
        recalcular()
    _crear_admin_inicial()
    tarea = asyncio.create_task(programador.ciclo()) if programador.activo() else None
    yield
    if tarea:
        tarea.cancel()


app = FastAPI(title="TurisData – Observatorio Turístico de Cuenca", version="0.1.0", lifespan=inicio)
app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGENES, allow_methods=["*"], allow_headers=["*"])
app.include_router(publico.router)
app.include_router(auth.router)
app.include_router(admin.router)


@app.get("/api/salud", tags=["sistema"])
def salud():
    return {"estado": "ok"}
