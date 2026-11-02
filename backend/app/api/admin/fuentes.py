"""Fuentes de datos y extracciones automáticas (RF-02, RF-04)."""
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text

from ...extractores import EXTRACTORES
from ...extractores.base import ejecucion_en_curso
from ...nucleo.db import fila, filas, transaccion
from ...nucleo.seguridad import ROLES_GESTION, ROLES_INTERNOS, auditar, requiere

router = APIRouter()


class CambioFuente(BaseModel):
    frecuencia_extraccion_dias: int | None = Field(default=None, gt=0, le=365)
    activa: bool | None = None


@router.get("/fuentes")
def listar(u=Depends(requiere(*ROLES_INTERNOS))):
    """Cada fuente con su última ejecución, última actualización correcta y próxima revisión."""
    return filas("""
        SELECT f.codigo, f.nombre, f.entidad_propietaria, f.tipo_fuente, f.formato, f.cobertura_geografica,
               f.extractor, f.frecuencia_extraccion_dias, f.activa, f.observaciones,
               ult.estado AS ultimo_estado, ult.iniciada_en AS ultima_ejecucion, ult.terminada_en AS ultima_fin,
               ult.mensaje AS ultimo_mensaje, ult.registros_nuevos, ult.registros_actualizados,
               ok.ultima AS ultima_correcta,
               CASE WHEN f.extractor IS NOT NULL AND f.frecuencia_extraccion_dias IS NOT NULL AND f.activa
                    THEN coalesce(ok.ultima + make_interval(days => f.frecuencia_extraccion_dias), now()) END
                   AS proxima_revision,
               coalesce(dat.total, 0) AS datos_vigentes,
               carga.ultima AS ultima_carga_manual
        FROM operativo.fuente_datos f
        LEFT JOIN LATERAL (SELECT * FROM operativo.ejecucion_extractor e WHERE e.fuente_id = f.id
                           ORDER BY e.id DESC LIMIT 1) ult ON true
        LEFT JOIN LATERAL (SELECT max(e.iniciada_en) AS ultima FROM operativo.ejecucion_extractor e
                           WHERE e.fuente_id = f.id AND e.estado IN ('ok', 'sin_cambios')) ok ON true
        LEFT JOIN LATERAL (SELECT count(*) AS total FROM operativo.observacion_externa o
                           JOIN operativo.variable_externa v ON v.codigo = o.variable
                           WHERE v.fuente_id = f.id AND o.vigente) dat ON true
        LEFT JOIN LATERAL (SELECT max(c.recibido_en) AS ultima FROM operativo.carga_datos c
                           WHERE c.fuente_id = f.id AND c.estado IN ('publicada', 'con_errores')) carga ON true
        WHERE f.tipo_fuente <> 'sistema'
        ORDER BY f.extractor IS NULL, f.nombre""")


@router.get("/fuentes/{codigo}/ejecuciones")
def ejecuciones(codigo: str, u=Depends(requiere(*ROLES_INTERNOS))):
    return filas("""
        SELECT e.id, e.iniciada_en, e.terminada_en, e.estado, e.registros_nuevos, e.registros_actualizados,
               e.mensaje, us.nombre AS usuario
        FROM operativo.ejecucion_extractor e
        JOIN operativo.fuente_datos f ON f.id = e.fuente_id
        LEFT JOIN operativo.usuario us ON us.id = e.usuario_id
        WHERE f.codigo = :c ORDER BY e.id DESC LIMIT 20""", c=codigo)


@router.post("/fuentes/{codigo}/ejecutar", status_code=202)
def ejecutar(codigo: str, tareas: BackgroundTasks, u=Depends(requiere(*ROLES_GESTION))):
    fuente = fila("SELECT extractor FROM operativo.fuente_datos WHERE codigo = :c", c=codigo)
    if not fuente or fuente["extractor"] not in EXTRACTORES:
        raise HTTPException(404, "Esta fuente no tiene extracción automática")
    if ejecucion_en_curso(codigo):
        raise HTTPException(409, "La extracción de esta fuente ya está en curso")
    # Corre en segundo plano: algunas fuentes tardan minutos por la pausa que exigen los sitios
    tareas.add_task(EXTRACTORES[fuente["extractor"]]().ejecutar, usuario_id=u["id"], forzar=True)
    auditar(u["id"], "extraccion", "fuente_datos", codigo)
    return {"mensaje": "Extracción iniciada"}


@router.patch("/fuentes/{codigo}")
def editar(codigo: str, datos: CambioFuente, u=Depends(requiere("administrador"))):
    cambios = {k: v for k, v in datos.model_dump().items() if v is not None}
    if not cambios:
        return {"codigo": codigo}
    with transaccion() as con:
        actualizadas = con.execute(text(
            f"UPDATE operativo.fuente_datos SET {', '.join(f'{k} = :{k}' for k in cambios)} WHERE codigo = :codigo"),
            {**cambios, "codigo": codigo}).rowcount
    if not actualizadas:
        raise HTTPException(404, "Fuente no encontrada")
    auditar(u["id"], "cambio_config", "fuente_datos", codigo, detalle=cambios)
    return {"codigo": codigo}
