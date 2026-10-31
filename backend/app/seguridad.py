"""Contraseñas (scrypt), tokens JWT, control de acceso por rol y auditoría."""
import hashlib
import hmac
import json
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import text

from .config import JWT_HORAS, JWT_SECRET
from .db import fila, transaccion

_bearer = HTTPBearer(auto_error=False)
_SCRYPT = dict(n=2**14, r=8, p=1, dklen=32)


def hash_contrasena(contrasena: str) -> str:
    sal = secrets.token_bytes(16)
    clave = hashlib.scrypt(contrasena.encode(), salt=sal, **_SCRYPT)
    return f"scrypt${sal.hex()}${clave.hex()}"


def verificar_contrasena(contrasena: str, guardado: str) -> bool:
    try:
        _, sal, clave = guardado.split("$")
    except ValueError:
        return False
    calculada = hashlib.scrypt(contrasena.encode(), salt=bytes.fromhex(sal), **_SCRYPT)
    return hmac.compare_digest(calculada.hex(), clave)


def crear_token(usuario: dict) -> str:
    datos = {
        "sub": str(usuario["id"]),
        "rol": usuario["rol"],
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_HORAS),
    }
    return jwt.encode(datos, JWT_SECRET, algorithm="HS256")


def usuario_actual(cred: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> dict:
    if cred is None:
        raise HTTPException(401, "Inicie sesión")
    try:
        datos = jwt.decode(cred.credentials, JWT_SECRET, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(401, "Sesión inválida o expirada")
    usuario = fila(
        """SELECT u.id, u.correo, u.nombre, u.rol, u.establecimiento_id, u.activo,
                  e.codigo_camara, e.nombre_comercial
           FROM operativo.usuario u
           LEFT JOIN operativo.establecimiento e ON e.id = u.establecimiento_id
           WHERE u.id = :id""", id=int(datos["sub"]))
    if not usuario or not usuario["activo"]:
        raise HTTPException(401, "Usuario inactivo")
    return usuario


def requiere(*roles: str):
    def dependencia(usuario: dict = Depends(usuario_actual)) -> dict:
        if usuario["rol"] not in roles:
            auditar(usuario["id"], "acceso", resultado="denegado", detalle={"requiere": roles})
            raise HTTPException(403, "No tiene permisos para esta acción")
        return usuario
    return dependencia


def auditar(usuario_id, accion, entidad=None, entidad_id=None, resultado="ok", detalle=None):
    with transaccion() as con:
        con.execute(text(
            """INSERT INTO operativo.auditoria (usuario_id, accion, entidad, entidad_id, resultado, detalle)
               VALUES (:u, :a, :e, :eid, :r, CAST(:d AS jsonb))"""),
            dict(u=usuario_id, a=accion, e=entidad, eid=None if entidad_id is None else str(entidad_id),
                 r=resultado, d=json.dumps(detalle, default=str) if detalle is not None else None))


def ip_cliente(request: Request) -> str:
    return request.client.host if request.client else ""
