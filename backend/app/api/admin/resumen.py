"""Resumen del panel: indicadores internos de calidad Q1–Q5 y conteos generales."""
from fastapi import APIRouter, Depends

from ...nucleo.db import fila, filas
from ...nucleo.seguridad import ROLES_INTERNOS, requiere

router = APIRouter()


def _porcentaje(parte, total):
    return round(parte / total * 100, 1) if total else None


@router.get("/resumen")
def resumen(u=Depends(requiere(*ROLES_INTERNOS))):
    q1 = fila("""SELECT o.periodo_inicio AS periodo, o.valor FROM analitico.observacion o
                 JOIN operativo.geografia g ON g.id = o.geografia_id
                 WHERE o.indicador_codigo = 'Q1' AND g.nivel = 'canton'
                 ORDER BY o.periodo_inicio DESC LIMIT 1""")
    ultima = fila("""SELECT id, recibido_en, registros_recibidos, registros_validos,
                            campos_criticos_esperados, campos_criticos_validos
                     FROM operativo.carga_datos WHERE estado <> 'recibida' ORDER BY id DESC LIMIT 1""")
    # Última actualización correcta de cada fuente: carga manual o extracción automática
    fuentes = filas("""
        SELECT f.codigo, f.nombre, f.sla_dias, f.prioritaria, u.ultima AS ultima_carga,
               extract(epoch FROM now() - u.ultima) / 86400 AS dias
        FROM operativo.fuente_datos f
        LEFT JOIN LATERAL (
            SELECT max(t) AS ultima FROM (
                SELECT c.recibido_en AS t FROM operativo.carga_datos c
                WHERE c.fuente_id = f.id AND c.estado IN ('publicada', 'con_errores')
                UNION ALL
                SELECT e.terminada_en FROM operativo.ejecucion_extractor e
                WHERE e.fuente_id = f.id AND e.estado IN ('ok', 'sin_cambios')) x) u ON true
        WHERE f.activa AND f.tipo_fuente <> 'sistema'
        ORDER BY f.prioritaria DESC, f.nombre""")
    prioritarias = [f for f in fuentes if f["prioritaria"]]
    al_dia = [f for f in prioritarias if f["dias"] is not None and f["sla_dias"] and f["dias"] <= f["sla_dias"]]

    return {
        "q1_cobertura": {"periodo": q1["periodo"], "valor": float(q1["valor"])} if q1 and q1["valor"] is not None else None,
        "q2_completitud": _porcentaje(ultima["campos_criticos_validos"], ultima["campos_criticos_esperados"]) if ultima else None,
        "q3_frescura": [{**f, "dias": round(float(f["dias"]), 1) if f["dias"] is not None else None} for f in fuentes],
        "q4_fuentes_al_dia": _porcentaje(len(al_dia), len(prioritarias)),
        "q5_registros_validos": _porcentaje(ultima["registros_validos"], ultima["registros_recibidos"]) if ultima else None,
        "conteos": fila("""SELECT
            (SELECT count(*) FROM operativo.establecimiento WHERE participa_hasta IS NULL) AS establecimientos,
            (SELECT count(*) FROM operativo.usuario WHERE activo) AS usuarios,
            (SELECT count(*) FROM operativo.carga_datos) AS cargas,
            (SELECT count(*) FROM operativo.reporte_alojamiento_mensual WHERE vigente) AS reportes"""),
        "metas": {r["clave"]: r["valor"] for r in filas("SELECT clave, valor FROM operativo.parametro")},
    }
