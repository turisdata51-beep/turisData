"""Carga de archivos de los establecimientos (RF-03, RF-09) y consulta de sus reportes."""
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from ...nucleo.config import PLANTILLA_ALOJAMIENTO
from ...nucleo.db import fila, filas
from ...nucleo.seguridad import ROLES_TODOS, auditar, requiere
from ...servicios.carga_alojamiento import importar

router = APIRouter()

TAMANO_MAXIMO = 5 * 1024 * 1024


@router.get("/plantilla")
def plantilla(u=Depends(requiere(*ROLES_TODOS))):
    return FileResponse(PLANTILLA_ALOJAMIENTO, filename=PLANTILLA_ALOJAMIENTO.name)


@router.post("/cargas")
async def subir(archivo: UploadFile = File(...), u=Depends(requiere("administrador", "analista", "asociado"))):
    contenido = await archivo.read()
    if len(contenido) > TAMANO_MAXIMO:
        raise HTTPException(413, "El archivo supera los 5 MB")
    resultado = importar(contenido, archivo.filename or "archivo", u)
    auditar(u["id"], "carga", "carga_datos", resultado["id"],
            "ok" if resultado["estado"] != "rechazada" else "error",
            {"archivo": archivo.filename, "estado": resultado["estado"], "validos": resultado["registros_validos"]})
    return resultado


@router.get("/cargas")
def cargas(u=Depends(requiere(*ROLES_TODOS))):
    return filas("""
        SELECT c.id, c.nombre_archivo, c.recibido_en, c.estado, c.registros_recibidos, c.registros_validos,
               c.registros_rechazados, f.nombre AS fuente, us.nombre AS usuario,
               (SELECT count(*) FROM operativo.carga_error e WHERE e.carga_id = c.id AND e.severidad = 'error') AS errores,
               (SELECT count(*) FROM operativo.carga_error e WHERE e.carga_id = c.id AND e.severidad = 'advertencia') AS advertencias
        FROM operativo.carga_datos c
        JOIN operativo.fuente_datos f ON f.id = c.fuente_id
        LEFT JOIN operativo.usuario us ON us.id = c.usuario_id
        WHERE (:asociado = false OR c.usuario_id = :uid)
        ORDER BY c.id DESC LIMIT 200""", asociado=u["rol"] == "asociado", uid=u["id"])


@router.get("/cargas/{carga_id}/errores")
def errores(carga_id: int, u=Depends(requiere(*ROLES_TODOS))):
    carga = fila("SELECT usuario_id FROM operativo.carga_datos WHERE id = :c", c=carga_id)
    if not carga or (u["rol"] == "asociado" and carga["usuario_id"] != u["id"]):
        raise HTTPException(404, "Carga no encontrada")
    return filas("""SELECT fila, campo, valor, regla, mensaje, severidad FROM operativo.carga_error
                    WHERE carga_id = :c ORDER BY fila NULLS FIRST, id""", c=carga_id)


@router.get("/mis-reportes")
def mis_reportes(u=Depends(requiere("asociado"))):
    return filas("""SELECT periodo, habitaciones_noche_disponibles, habitaciones_noche_ocupadas,
                           llegadas_residentes + llegadas_no_residentes AS llegadas,
                           noches_residentes + noches_no_residentes AS noches, ingreso_habitaciones_usd
                    FROM operativo.reporte_alojamiento_mensual
                    WHERE establecimiento_id = :e AND vigente ORDER BY periodo DESC""", e=u["establecimiento_id"])
