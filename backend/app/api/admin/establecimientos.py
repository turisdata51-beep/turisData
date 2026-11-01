"""Padrón de establecimientos asociados que reportan al observatorio."""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from ...nucleo.db import fila, filas, transaccion
from ...nucleo.seguridad import ROLES_GESTION, auditar, requiere, usuario_actual
from ...servicios.indicadores import recalcular

router = APIRouter()


class Establecimiento(BaseModel):
    codigo_camara: str = Field(min_length=2, max_length=30)
    nombre_comercial: str = Field(min_length=2)
    tipo_alojamiento: str
    categoria: str
    parroquia: str
    participa_desde: date
    participa_hasta: date | None = None


@router.get("/parroquias")
def parroquias(u=Depends(usuario_actual)):
    return filas("SELECT id, nombre, tipo FROM operativo.geografia WHERE nivel = 'parroquia' ORDER BY tipo DESC, nombre")


@router.get("/establecimientos")
def establecimientos(u=Depends(requiere(*ROLES_GESTION))):
    return filas("""
        SELECT e.id, e.codigo_camara, e.nombre_comercial, e.tipo_alojamiento, e.categoria, g.nombre AS parroquia,
               e.participa_desde, e.participa_hasta,
               (SELECT max(periodo) FROM operativo.reporte_alojamiento_mensual r
                WHERE r.establecimiento_id = e.id AND r.vigente) AS ultimo_reporte
        FROM operativo.establecimiento e JOIN operativo.geografia g ON g.id = e.parroquia_id
        ORDER BY e.codigo_camara""")


def _guardar(datos: Establecimiento, establecimiento_id: int | None) -> int:
    parroquia = fila("SELECT id FROM operativo.geografia WHERE nivel = 'parroquia' AND nombre = :n", n=datos.parroquia)
    if not parroquia:
        raise HTTPException(400, "Parroquia no válida")
    valores = {**datos.model_dump(), "parroquia_id": parroquia["id"], "id": establecimiento_id}
    try:
        with transaccion() as con:
            if establecimiento_id is None:
                return con.execute(text("""
                    INSERT INTO operativo.establecimiento
                      (codigo_camara, nombre_comercial, tipo_alojamiento, categoria, parroquia_id, participa_desde, participa_hasta)
                    VALUES (:codigo_camara, :nombre_comercial, :tipo_alojamiento, :categoria, :parroquia_id,
                            :participa_desde, :participa_hasta) RETURNING id"""), valores).scalar()
            con.execute(text("""
                UPDATE operativo.establecimiento SET codigo_camara = :codigo_camara, nombre_comercial = :nombre_comercial,
                  tipo_alojamiento = :tipo_alojamiento, categoria = :categoria, parroquia_id = :parroquia_id,
                  participa_desde = :participa_desde, participa_hasta = :participa_hasta
                WHERE id = :id"""), valores)
            return establecimiento_id
    except IntegrityError:
        raise HTTPException(409, "Ya existe un establecimiento con ese código, o las fechas no son coherentes")


@router.post("/establecimientos")
def crear(datos: Establecimiento, u=Depends(requiere(*ROLES_GESTION))):
    nuevo = _guardar(datos, None)
    auditar(u["id"], "crear", "establecimiento", nuevo, detalle=datos.model_dump())
    return {"id": nuevo}


@router.put("/establecimientos/{establecimiento_id}")
def editar(establecimiento_id: int, datos: Establecimiento, u=Depends(requiere(*ROLES_GESTION))):
    _guardar(datos, establecimiento_id)
    auditar(u["id"], "editar", "establecimiento", establecimiento_id, detalle=datos.model_dump())
    recalcular()  # cambiar fechas de participación afecta la cobertura (Q1)
    return {"id": establecimiento_id}
