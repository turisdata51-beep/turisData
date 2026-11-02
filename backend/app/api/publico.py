"""API pública: lo que muestran el sitio y el observatorio sin iniciar sesión.

Solo devuelve observaciones publicables (respetan el mínimo de confidencialidad).
Los indicadores se filtran por zona (cantón o parroquia) o por categoría de
alojamiento; la categoría solo existe a nivel cantonal.
"""
import json
from datetime import date

from fastapi import APIRouter, HTTPException, Query

from ..nucleo.db import fila, filas
from ..servicios.diccionario import cargar

router = APIRouter(prefix="/api/public", tags=["público"])

KPI_PORTADA = ["A1", "A2", "A4", "B4", "B6", "B7", "A5", "D4"]
CANTON = "Cuenca"


def _filtro(zona: str | None, categoria: str | None) -> tuple[int, str]:
    """(geografia_id, dimensiones en JSON) para la zona y la categoría pedidas."""
    nombre = CANTON if categoria else (zona or CANTON)
    geografia = fila("SELECT id FROM operativo.geografia WHERE nombre = :n", n=nombre)
    if not geografia:
        raise HTTPException(404, f"No existe la zona {nombre}")
    return geografia["id"], json.dumps({"categoria": categoria} if categoria else {}, ensure_ascii=False)


_SQL_OBSERVACIONES = """
    SELECT o.indicador_codigo AS codigo, o.periodo_inicio AS periodo, o.valor, o.bandera,
           o.n_unidades, o.cobertura_pct, o.publicable
    FROM analitico.observacion o
    WHERE o.geografia_id = :g AND o.dimensiones = CAST(:dims AS jsonb)
"""


def _ultimo_periodo(geografia_id: int, dims: str) -> date | None:
    r = fila(_SQL_OBSERVACIONES + " AND o.indicador_codigo = 'B4' AND o.publicable ORDER BY o.periodo_inicio DESC LIMIT 1",
             g=geografia_id, dims=dims)
    return r["periodo"] if r else None


def _por_periodo(datos: list[dict], clave: str) -> list[dict]:
    """Pasa filas (periodo, clave, valor) a una fila por período, como esperan los gráficos."""
    resultado: dict = {}
    for r in datos:
        resultado.setdefault(r["periodo"], {"periodo": r["periodo"]})[r[clave]] = float(r["valor"])
    return list(resultado.values())


@router.get("/contenido")
def contenido():
    r = fila("SELECT valor FROM operativo.contenido_sitio WHERE clave = 'landing'")
    return r["valor"] if r else {}


@router.get("/filtros")
def filtros():
    """Opciones disponibles: meses publicados, zonas y categorías con datos publicables."""
    canton = fila("SELECT id FROM operativo.geografia WHERE nivel = 'canton' AND nombre = :n", n=CANTON)
    periodos = [r["periodo"] for r in filas(
        _SQL_OBSERVACIONES + " AND o.indicador_codigo = 'B4' AND o.publicable ORDER BY o.periodo_inicio",
        g=canton["id"], dims="{}")]
    parroquias = [r["nombre"] for r in filas(
        """SELECT DISTINCT g.nombre FROM analitico.observacion o JOIN operativo.geografia g ON g.id = o.geografia_id
           WHERE g.nivel = 'parroquia' AND o.indicador_codigo = 'B4' AND o.publicable AND o.dimensiones = '{}'::jsonb
           ORDER BY g.nombre""")]
    categorias = [r["categoria"] for r in filas(
        """SELECT DISTINCT o.dimensiones->>'categoria' AS categoria FROM analitico.observacion o
           WHERE o.indicador_codigo = 'B4' AND o.publicable AND o.dimensiones ? 'categoria' ORDER BY 1""")]
    return {"periodos": periodos, "zonas": [CANTON, *parroquias], "categorias": categorias}


@router.get("/periodos")
def periodos():
    return filtros()["periodos"]


@router.get("/resumen")
def resumen(periodo: date | None = None, zona: str | None = None, categoria: str | None = None):
    geografia_id, dims = _filtro(zona, categoria)
    periodo = periodo or _ultimo_periodo(geografia_id, dims)
    if periodo is None:
        return {"periodo": None, "kpis": [], "ultima_actualizacion": None}
    anterior = date(periodo.year - 1, periodo.month, 1)
    valores = {(r["codigo"], r["periodo"]): r for r in filas(
        _SQL_OBSERVACIONES + " AND o.periodo_inicio IN (:p, :a) AND o.indicador_codigo = ANY(:c)",
        g=geografia_id, dims=dims, p=periodo, a=anterior, c=KPI_PORTADA)}
    fichas = {f["codigo"]: f for f in cargar()["indicadores"]}
    kpis = []
    for codigo in KPI_PORTADA:
        actual, previo = valores.get((codigo, periodo)), valores.get((codigo, anterior))
        if not actual:  # el indicador no se calcula para este filtro (p. ej. D4 en una parroquia)
            continue
        valor = float(actual["valor"]) if actual["publicable"] else None
        base = float(previo["valor"]) if previo and previo["publicable"] else None
        variacion = None
        if valor is not None and base:  # base cero o inexistente = no calculable (Manual, Anexo A)
            variacion = round((valor - base) / base * 100, 1)
        kpis.append(dict(
            codigo=codigo, nombre=fichas[codigo]["nombre"], unidad=fichas[codigo]["unidad"],
            valor=valor, valor_anio_anterior=base, variacion_interanual=variacion, bandera=actual["bandera"],
            n_unidades=actual["n_unidades"],
            cobertura_pct=float(actual["cobertura_pct"]) if actual["cobertura_pct"] is not None else None))
    actualizado = fila(
        """SELECT max(c.recibido_en) AS t FROM operativo.carga_datos c
           JOIN operativo.fuente_datos f ON f.id = c.fuente_id
           WHERE f.codigo = 'plantilla_alojamiento_camara' AND c.estado IN ('publicada', 'con_errores')""")
    return {"periodo": periodo, "kpis": kpis, "ultima_actualizacion": actualizado["t"] if actualizado else None}


@router.get("/series")
def series(codigos: str = Query("B4,A1"), desde: date | None = None, hasta: date | None = None,
           zona: str | None = None, categoria: str | None = None):
    geografia_id, dims = _filtro(zona, categoria)
    lista = [c.strip().upper() for c in codigos.split(",") if c.strip()]
    return _por_periodo(filas(
        _SQL_OBSERVACIONES + """ AND o.publicable AND o.indicador_codigo = ANY(:c)
           AND (CAST(:d AS date) IS NULL OR o.periodo_inicio >= :d)
           AND (CAST(:h AS date) IS NULL OR o.periodo_inicio <= :h)
           ORDER BY o.periodo_inicio""", g=geografia_id, dims=dims, c=lista, d=desde, h=hasta), "codigo")


@router.get("/residencia")
def residencia(codigo: str = "A2", desde: date | None = None, hasta: date | None = None, zona: str | None = None):
    if codigo not in ("A1", "A2"):
        raise HTTPException(400, "Solo A1 o A2")
    geografia_id, _ = _filtro(zona, None)
    return _por_periodo(filas(
        """SELECT o.periodo_inicio AS periodo, o.dimensiones->>'residencia' AS residencia, o.valor
           FROM analitico.observacion o
           WHERE o.geografia_id = :g AND o.publicable AND o.indicador_codigo = :c AND o.dimensiones ? 'residencia'
             AND (CAST(:d AS date) IS NULL OR o.periodo_inicio >= :d)
             AND (CAST(:h AS date) IS NULL OR o.periodo_inicio <= :h)
           ORDER BY o.periodo_inicio""", g=geografia_id, c=codigo, d=desde, h=hasta), "residencia")


@router.get("/parroquias")
def parroquias(periodo: date | None = None):
    canton_id, dims = _filtro(None, None)
    periodo = periodo or _ultimo_periodo(canton_id, dims)
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


def _ultima_extraccion(fuente: str):
    r = fila("""SELECT max(e.terminada_en) AS t FROM operativo.ejecucion_extractor e
                JOIN operativo.fuente_datos f ON f.id = e.fuente_id
                WHERE f.codigo = :f AND e.estado IN ('ok', 'sin_cambios')""", f=fuente)
    return r["t"] if r else None


@router.get("/economia")
def economia():
    """Ventas mensuales de alojamiento y comidas en Cuenca (SRI, sección CIIU I)."""
    mensual = [{"periodo": r["periodo"], "ventas": float(r["valor"])} for r in filas(
        """SELECT o.periodo_inicio AS periodo, o.valor FROM operativo.observacion_externa o
           JOIN operativo.geografia g ON g.id = o.geografia_id
           WHERE o.variable = 'sri_ventas_seccion_i' AND o.vigente AND g.nivel = 'canton'
           ORDER BY o.periodo_inicio""")]
    if not mensual:
        return {"mensual": [], "anual": [], "ultimo": None, "actualizado": None}
    por_mes = {(m["periodo"].year, m["periodo"].month): m["ventas"] for m in mensual}
    ultimo = mensual[-1]["periodo"]
    anual = []
    for anio in sorted({a for a, _ in por_mes}):
        meses = [v for (a, _), v in por_mes.items() if a == anio]
        anual.append({"anio": anio, "ventas": sum(meses), "meses": len(meses)})

    # Acumulado del año hasta el último mes publicado, frente al mismo tramo del año anterior
    acumulado = sum(por_mes.get((ultimo.year, m), 0) for m in range(1, ultimo.month + 1))
    acumulado_anterior = sum(por_mes.get((ultimo.year - 1, m), 0) for m in range(1, ultimo.month + 1))
    mes_anterior = por_mes.get((ultimo.year - 1, ultimo.month))

    def variacion(actual, base):
        return round((actual - base) / base * 100, 1) if base else None

    return {
        "mensual": mensual,
        "anual": anual,
        "ultimo": {
            "periodo": ultimo, "ventas": mensual[-1]["ventas"],
            "variacion_interanual": variacion(mensual[-1]["ventas"], mes_anterior),
            "acumulado": acumulado, "acumulado_anterior": acumulado_anterior,
            "variacion_acumulada": variacion(acumulado, acumulado_anterior),
        },
        "actualizado": _ultima_extraccion("sri_ventas"),
    }


@router.get("/oferta")
def oferta():
    """Oferta registrada: catastro turístico (por actividad, clasificación y parroquia) y capacidad municipal."""
    def ultimo_corte(variable: str):
        r = fila("""SELECT max(periodo_inicio) AS p FROM operativo.observacion_externa
                    WHERE variable = :v AND vigente""", v=variable)
        return r["p"] if r else None

    def datos(variable: str, corte, nivel: str):
        return filas("""SELECT g.nombre, g.tipo, o.dimensiones, o.valor FROM operativo.observacion_externa o
                        JOIN operativo.geografia g ON g.id = o.geografia_id
                        WHERE o.variable = :v AND o.vigente AND o.periodo_inicio = :p AND g.nivel = :n""",
                     v=variable, p=corte, n=nivel)

    corte_catastro = ultimo_corte("catastro_establecimientos")
    catastro_canton = datos("catastro_establecimientos", corte_catastro, "canton")
    catastro_parroquias = datos("catastro_establecimientos", corte_catastro, "parroquia")
    por_actividad = sorted(({"actividad": d["dimensiones"]["actividad"], "establecimientos": int(d["valor"])}
                            for d in catastro_canton if list(d["dimensiones"]) == ["actividad"]),
                           key=lambda x: -x["establecimientos"])
    por_clasificacion = sorted(({"clasificacion": d["dimensiones"]["clasificacion"], "establecimientos": int(d["valor"])}
                                for d in catastro_canton if "clasificacion" in d["dimensiones"]),
                               key=lambda x: -x["establecimientos"])
    por_parroquia = sorted(({"parroquia": d["nombre"], "tipo": d["tipo"], "alojamientos": int(d["valor"])}
                            for d in catastro_parroquias if d["dimensiones"].get("actividad") == "ALOJAMIENTO"),
                           key=lambda x: -x["alojamientos"])

    corte_hosteleria = ultimo_corte("hosteleria_plazas")
    capacidad: dict = {}
    for variable in ("hosteleria_establecimientos", "hosteleria_habitaciones", "hosteleria_plazas"):
        for d in datos(variable, corte_hosteleria, "canton"):
            tipo = d["dimensiones"].get("tipo", "TOTAL")
            capacidad.setdefault(tipo, {"tipo": tipo})[variable.removeprefix("hosteleria_")] = int(d["valor"])
    total = capacidad.pop("TOTAL", None)

    d6 = fila("""SELECT o.valor, o.denominador, o.bandera FROM analitico.observacion o
                 WHERE o.indicador_codigo = 'D6' AND o.publicable ORDER BY o.periodo_inicio DESC LIMIT 1""")
    return {
        "catastro": {"corte": corte_catastro, "por_actividad": por_actividad, "alojamiento_por_clasificacion": por_clasificacion,
                     "alojamiento_por_parroquia": por_parroquia, "actualizado": _ultima_extraccion("catastro_turistico")},
        "capacidad": {"corte": corte_hosteleria, "total": total,
                      "por_tipo": sorted(capacidad.values(), key=lambda x: -x.get("plazas", 0)),
                      "actualizado": _ultima_extraccion("hosteleria_cuenca")},
        "plazas_por_100": {"valor": float(d6["valor"]), "poblacion": float(d6["denominador"]), "bandera": d6["bandera"]} if d6 else None,
    }


SOSTENIBILIDAD = ["D3", "E1", "E6", "E3", "E4", "E5"]
FUENTES_SOSTENIBILIDAD = ["plantilla_empleo_camara", "plantilla_accesibilidad_camara", "plantilla_consumos_camara"]


@router.get("/sostenibilidad")
def sostenibilidad():
    """Empleo estacional, accesibilidad, certificaciones y consumos por noche (cantón, plantillas de la Cámara).

    La serie incluye los períodos confidenciales con valor nulo para que el gráfico muestre el hueco.
    """
    geografia_id, dims = _filtro(None, None)
    datos = filas(_SQL_OBSERVACIONES + " AND o.indicador_codigo = ANY(:c) ORDER BY o.periodo_inicio",
                  g=geografia_id, dims=dims, c=SOSTENIBILIDAD)
    fichas = {f["codigo"]: f for f in cargar()["indicadores"]}
    resultado = []
    for codigo in SOSTENIBILIDAD:
        serie = [dict(periodo=d["periodo"], valor=float(d["valor"]) if d["publicable"] else None,
                      n_unidades=d["n_unidades"]) for d in datos if d["codigo"] == codigo]
        ficha = fichas[codigo]
        resultado.append(dict(
            codigo=codigo, nombre=ficha["nombre"], unidad=ficha["unidad"], periodicidad=ficha["periodicidad"],
            definicion=ficha["definicion_negocio"], limitaciones=ficha["limitaciones"],
            ultimo=next((s for s in reversed(serie) if s["valor"] is not None), None), serie=serie))
    actualizado = fila("""SELECT max(c.recibido_en) AS t FROM operativo.carga_datos c
                          JOIN operativo.fuente_datos f ON f.id = c.fuente_id
                          WHERE f.codigo = ANY(:f) AND c.estado IN ('publicada', 'con_errores')""", f=FUENTES_SOSTENIBILIDAD)
    return {"indicadores": resultado, "actualizado": actualizado["t"] if actualizado else None}


@router.get("/indicadores")
def indicadores():
    campos = ("codigo", "nombre", "tipo_base", "definicion_negocio", "definicion_estadistica", "formula_texto",
              "unidad", "periodicidad", "limitaciones", "referencias", "fase")
    return [{c: f.get(c) for c in campos} for f in cargar()["indicadores"]]
