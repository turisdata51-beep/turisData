"""Inicio de sesión y datos del usuario autenticado."""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import text

from ..nucleo.db import fila, transaccion
from ..nucleo.seguridad import auditar, crear_token, ip_cliente, usuario_actual, verificar_contrasena

router = APIRouter(prefix="/api/auth", tags=["auth"])


class Credenciales(BaseModel):
    correo: str
    contrasena: str


@router.post("/login")
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


@router.get("/yo")
def yo(u=Depends(usuario_actual)):
    return u
