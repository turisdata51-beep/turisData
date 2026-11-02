"""Ejecución automática de los extractores.

Corre dentro de la API como tarea de fondo. Cada cierto tiempo revisa las fuentes
con extractor y ejecuta las que ya cumplieron su frecuencia
(operativo.fuente_datos.frecuencia_extraccion_dias) desde su última ejecución
correcta. Las ejecuciones son de a una, para no saturar los sitios.

Se desactiva con EXTRACCION_AUTOMATICA=0 en backend/.env (por ejemplo, si en
producción se usa un cron externo). Con varias réplicas de la API, activarla solo
en una.
"""
import asyncio
import logging
import os

from ..extractores import EXTRACTORES
from ..extractores.base import ejecucion_en_curso
from ..nucleo.db import filas

log = logging.getLogger("uvicorn.error")  # aparece junto al registro de la API

ESPERA_INICIAL_SEGUNDOS = 60       # deja arrancar la API antes de la primera revisión
INTERVALO_REVISION_SEGUNDOS = 15 * 60


def activo() -> bool:
    return os.environ.get("EXTRACCION_AUTOMATICA", "1") != "0"


def fuentes_pendientes() -> list[str]:
    """Extractores cuya última ejecución correcta es más antigua que su frecuencia."""
    return [f["extractor"] for f in filas("""
        SELECT f.extractor
        FROM operativo.fuente_datos f
        LEFT JOIN LATERAL (
            SELECT max(e.iniciada_en) AS ultima FROM operativo.ejecucion_extractor e
            WHERE e.fuente_id = f.id AND e.estado IN ('ok', 'sin_cambios')) u ON true
        WHERE f.activa AND f.extractor IS NOT NULL AND f.frecuencia_extraccion_dias IS NOT NULL
          AND (u.ultima IS NULL OR u.ultima < now() - make_interval(days => f.frecuencia_extraccion_dias))
        ORDER BY u.ultima NULLS FIRST""") if f["extractor"] in EXTRACTORES]


def ejecutar_pendientes() -> list[dict]:
    resultados = []
    for nombre in fuentes_pendientes():
        extractor = EXTRACTORES[nombre]
        if ejecucion_en_curso(extractor.fuente_codigo):
            continue
        resultado = extractor().ejecutar()
        log.info("Extracción automática %s: %s (%s)", nombre, resultado["estado"], resultado["mensaje"])
        resultados.append({"extractor": nombre, **resultado})
    return resultados


async def ciclo():
    await asyncio.sleep(ESPERA_INICIAL_SEGUNDOS)
    while True:
        try:
            await asyncio.to_thread(ejecutar_pendientes)
        except Exception:  # un fallo no debe detener las siguientes revisiones
            log.exception("Fallo en la revisión de extracciones automáticas")
        await asyncio.sleep(INTERVALO_REVISION_SEGUNDOS)
