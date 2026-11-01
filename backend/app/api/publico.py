"""API pública: lo que muestra la landing y el observatorio sin iniciar sesión.

Solo devuelve observaciones publicables (respetan el mínimo de confidencialidad).
"""
from datetime import date

from fastapi import APIRouter, HTTPException, Query

from ..nucleo.db import fila, filas
from ..servicios.diccionario import cargar

router = APIRouter(prefix="/api/public", tags=["público"])

KPI_PORTADA = ["A1", "A2", "A4", "B4", "B6", "B7", "A5", "D4"]

_SQL_CANTON = """
    SELECT o.indicador_codigo AS codigo, o.periodo_inicio AS periodo, o.valor, o.bandera,
           o.n_unidades, o.cobertura_pct, o.publicable
    FROM analitico.observacion o
    JOIN operativo.geografia g ON g.id = o.geografia_id
    WHERE g.nivel = 'canton' AND o.dimensiones = '{}'::jsonb
"""


def _ultimo_periodo() -> date | None:
    r = fila(_SQL_CANTON + " AND o.indicador_codigo = 'B4' AND o.publicable ORDER BY o.periodo_inicio DESC LIMIT 1")
    return r["periodo"] if r else None


@router.get("/contenido")
def contenido():
    r = fila("SELECT valor FROM operativo.contenido_sitio WHERE clave = 'landing'")
    return r["valor"] if r else {}


@router.get("/periodos")
def periodos():
    return [r["periodo"] for r in filas(
        _SQL_CANTON + " AND o.indicador_codigo = 'B4' AND o.publicable ORDER BY o.periodo_inicio")]


@router.get("/resumen")
def resumen(periodo: date | None = None):
    periodo = periodo or _ultimo_periodo()
    if periodo is None:
        return {"periodo": None, "kpis": []}
    anterior = date(periodo.year - 1, periodo.month, 1)
    valores = {(r["codigo"], r["periodo"]): r for r in filas(
        _SQL_CANTON + " AND o.periodo_inicio IN (:p, :a) AND o.indicador_codigo = ANY(:c)",
        p=periodo, a=anterior, c=KPI_PORTADA)}
    fichas = {f["codigo"]: f for f in cargar()["indicadores"]}
    kpis = []
    for codigo in KPI_PORTADA:
        actual, previo = valores.get((codigo, periodo)), valores.get((codigo, anterior))
        visible = actual and actual["publicable"]
        valor = float(actual["valor"]) if visible else None
        base = float(previo["valor"]) if previo and previo["publicable"] else None
        variacion = None
        if valor is not None and base:  # base cero o inexistente = no calculable (Manual, Anexo A)
            variacion = round((valor - base) / base * 100, 1)
        kpis.append(dict(
            codigo=codigo, nombre=fichas[codigo]["nombre"], unidad=fichas[codigo]["unidad"],
            valor=valor, valor_anio_anterior=base,
            variacion_interanual=variacion, bandera=actual["bandera"] if actual else None,
            n_unidades=actual["n_unidades"] if actual else None,
            cobertura_pct=float(actual["cobertura_pct"]) if actual and actual["cobertura_pct"] is not None else None))
    actualizado = fila(
        """SELECT max(c.recibido_en) AS t FROM operativo.carga_datos c
           JOIN operativo.fuente_datos f ON f.id = c.fuente_id
           WHERE f.codigo = 'plantilla_alojamiento_camara' AND c.estado IN ('publicada', 'con_errores')""")
    return {"periodo": periodo, "kpis": kpis, "ultima_actualizacion": actualizado["t"] if actualizado else None}


@router.get("/series")
def series(codigos: str = Query("B4,A1"), desde: date | None = None, hasta: date | None = None):
    lista = [c.strip().upper() for c in codigos.split(",") if c.strip()]
    datos = filas(
        _SQL_CANTON + """ AND o.publicable AND o.indicador_codigo = ANY(:c)
           AND (CAST(:d AS date) IS NULL OR o.periodo_inicio >= :d)
           AND (CAST(:h AS date) IS NULL OR o.periodo_inicio <= :h)
           ORDER BY o.periodo_inicio""", c=lista, d=desde, h=hasta)
    por_periodo: dict = {}
    for r in datos:
        por_periodo.setdefault(r["periodo"], {"periodo": r["periodo"]})[r["codigo"]] = float(r["valor"])
    return list(por_periodo.values())


@router.get("/residencia")
def residencia(codigo: str = "A2", desde: date | None = None, hasta: date | None = None):
    if codigo not in ("A1", "A2"):
        raise HTTPException(400, "Solo A1 o A2")
    datos = filas(
        """SELECT o.periodo_inicio AS periodo, o.dimensiones->>'residencia' AS residencia, o.valor
           FROM analitico.observacion o JOIN operativo.geografia g ON g.id = o.geografia_id
           WHERE g.nivel = 'canton' AND o.publicable AND o.indicador_codigo = :c
             AND o.dimensiones ? 'residencia'
             AND (CAST(:d AS date) IS NULL OR o.periodo_inicio >= :d)
             AND (CAST(:h AS date) IS NULL OR o.periodo_inicio <= :h)
           ORDER BY o.periodo_inicio""", c=codigo, d=desde, h=hasta)
    por_periodo: dict = {}
    for r in datos:
        por_periodo.setdefault(r["periodo"], {"periodo": r["periodo"]})[r["residencia"]] = float(r["valor"])
    return list(por_periodo.values())


@router.get("/parroquias")
def parroquias(periodo: date | None = None):
    periodo = periodo or _ultimo_periodo()
    datos = filas(
        """SELECT g.nombre AS parroquia, g.tipo, o.indicador_codigo AS codigo, o.valor, o.publicable, o.n_unidades
           FROM analitico.observacion o JOIN operativo.geografia g ON g.id = o.geografia_id
           WHERE g.nivel = 'parroquia' AND o.periodo_inicio = :p AND o.dimensiones = '{}'::jsonb
             AND o.indicador_codigo IN ('A1', 'A2', 'B4')""", p=periodo)
    resultado: dict = {}
    for r in datos:
        item = resultado.setdefault(r["parroquia"], {"parroquia": r["parroquia"], "tipo": r["tipo"], "confidencial": False})
        if r["publicable"]:
            item[r["codigo"]] = float(r["valor"])
        else:
            item["confidencial"] = True  # menos establecimientos que el mínimo: no se publica
    return {"periodo": periodo, "parroquias": sorted(resultado.values(), key=lambda x: -(x.get("A2") or 0))}


@router.get("/indicadores")
def indicadores():
    campos = ("codigo", "nombre", "tipo_base", "definicion_negocio", "definicion_estadistica", "formula_texto",
              "unidad", "periodicidad", "limitaciones", "referencias", "fase")
    return [{c: f.get(c) for c in campos} for f in cargar()["indicadores"]]
