"""Gestión de cuentas y roles (RF-01). Solo el administrador."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from ...nucleo.db import fila, filas, transaccion
from ...nucleo.seguridad import auditar, hash_contrasena, requiere

router = APIRouter()


class UsuarioNuevo(BaseModel):
    correo: EmailStr
    nombre: str = Field(min_length=2)
    rol: str
    contrasena: str = Field(min_length=10)
    codigo_establecimiento: str | None = None


class UsuarioCambio(BaseModel):
    nombre: str | None = None
    rol: str | None = None
    activo: bool | None = None
    contrasena: str | None = Field(default=None, min_length=10)


@router.get("/usuarios")
def listar(u=Depends(requiere("administrador"))):
    return filas("""SELECT u.id, u.correo, u.nombre, u.rol, u.activo, u.creado_en, u.ultimo_acceso,
                           e.codigo_camara AS establecimiento
                    FROM operativo.usuario u LEFT JOIN operativo.establecimiento e ON e.id = u.establecimiento_id
                    ORDER BY u.id""")


@router.post("/usuarios")
def crear(datos: UsuarioNuevo, u=Depends(requiere("administrador"))):
    establecimiento_id = None
    if datos.rol == "asociado":
        est = fila("SELECT id FROM operativo.establecimiento WHERE codigo_camara = :c", c=datos.codigo_establecimiento)
        if not est:
            raise HTTPException(400, "Un asociado necesita un código de establecimiento válido")
        establecimiento_id = est["id"]
    try:
        with transaccion() as con:
            nuevo = con.execute(text("""
                INSERT INTO operativo.usuario (correo, nombre, hash_contrasena, rol, establecimiento_id)
                VALUES (:c, :n, :h, :r, :e) RETURNING id"""),
                dict(c=datos.correo.lower(), n=datos.nombre, h=hash_contrasena(datos.contrasena),
                     r=datos.rol, e=establecimiento_id)).scalar()
    except IntegrityError:
        raise HTTPException(409, "El correo ya existe o el rol no es válido")
    auditar(u["id"], "crear", "usuario", nuevo, detalle={"correo": datos.correo, "rol": datos.rol})
    return {"id": nuevo}


@router.patch("/usuarios/{usuario_id}")
def editar(usuario_id: int, datos: UsuarioCambio, u=Depends(requiere("administrador"))):
    if usuario_id == u["id"] and (datos.activo is False or (datos.rol and datos.rol != "administrador")):
        raise HTTPException(400, "No puede desactivarse ni quitarse el rol de administrador a sí mismo")
    cambios = {k: v for k, v in datos.model_dump().items() if v is not None}
    if "contrasena" in cambios:
        cambios["hash_contrasena"] = hash_contrasena(cambios.pop("contrasena"))
    if not cambios:
        return {"id": usuario_id}
    try:
        with transaccion() as con:
            con.execute(text(f"""UPDATE operativo.usuario SET {', '.join(f'{k} = :{k}' for k in cambios)}
                                 WHERE id = :id"""), {**cambios, "id": usuario_id})
    except IntegrityError:
        raise HTTPException(400, "Cambio no válido (un asociado debe tener establecimiento)")
    auditar(u["id"], "editar", "usuario", usuario_id,
            detalle={k: v for k, v in cambios.items() if k != "hash_contrasena"})
    return {"id": usuario_id}
