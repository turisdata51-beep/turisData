"""Motor de cálculo: recalcula analitico.observacion desde los datos vigentes.

Dos orígenes:
- Reportes de los hoteles (vista analitico.v_alojamiento_mensual): los KPI se
  calculan sobre sumas, nunca promediando porcentajes de cada hotel. Un valor con
  menos establecimientos que el mínimo de confidencialidad se guarda con
  publicable = false.
- Fuentes externas extraídas por scraping (operativo.observacion_externa):
  registros públicos, por eso se publican siempre.
"""
import calendar
import json
from dataclasses import dataclass, field
from datetime import date

from sqlalchemy import text

from ..nucleo.db import transaccion


def _fin_de_periodo(inicio: date, periodicidad: str) -> date:
    meses = {"mensual": 1, "trimestral": 3, "anual": 12}[periodicidad]
    mes_final = inicio.month + meses - 1
    anio, mes = inicio.year + (mes_final - 1) // 12, (mes_final - 1) % 12 + 1
    return date(anio, mes, calendar.monthrange(anio, mes)[1])


def _division(numerador, denominador, factor=1):
    if numerador is None or not denominador:
        return None
    return float(numerador) / float(denominador) * factor


@dataclass
class _Calculo:
    """Acumula las filas de analitico.observacion de un recálculo."""
    versiones: dict
    minimo_publicacion: int
    fuentes: dict  # código de fuente -> id
    filas: list = field(default_factory=list)

    def agregar(self, codigo, periodo, geografia_id, valor, n, *, dimensiones=None, bandera="observado",
                fuentes=("plantilla_alojamiento_camara",), cargas=(), numerador=None, denominador=None,
                cobertura=None, publicable=None, periodicidad="mensual"):
        if codigo not in self.versiones:  # indicador no vigente en el diccionario
            return
        if publicable is None:
            publicable = n is not None and n >= self.minimo_publicacion
        self.filas.append(dict(
            codigo=codigo, version=self.versiones[codigo], ini=periodo, fin=_fin_de_periodo(periodo, periodicidad),
            periodicidad=periodicidad, geo=geografia_id,
            dims=json.dumps(dimensiones or {}, ensure_ascii=False),
            valor=None if valor is None else round(valor, 4),
            motivo="denominador cero o sin datos" if valor is None else None,
            num=numerador, den=denominador, bandera=bandera, n=n, cobertura=cobertura,
            publicable=valor is not None and publicable,
            fuentes=[self.fuentes[f] for f in fuentes if f in self.fuentes], cargas=list(cargas)))


def _poblacion(con) -> dict:
    """{(geografia_id, año): (habitantes, bandera)}.

    Usa la proyección del INEC de cada año (serie coherente, marcada como estimada).
    Si no hay proyección, el censo más reciente: observado si es del mismo año.
    """
    proyeccion = {(r.geografia_id, r.anio): r.valor for r in con.execute(text(
        """SELECT geografia_id, extract(year FROM periodo_inicio)::int AS anio, valor
           FROM operativo.observacion_externa
           WHERE variable = 'inec_poblacion_proyectada' AND periodicidad = 'anual' AND vigente"""))}
    censos = con.execute(text("SELECT geografia_id, anio, habitantes FROM operativo.poblacion ORDER BY anio")).all()

    class Poblacion(dict):
        def __missing__(self, clave):
            geografia_id, anio = clave
            if clave in proyeccion:
                return float(proyeccion[clave]), "estimado"
            previos = [c for c in censos if c.geografia_id == geografia_id and c.anio <= anio]
            if not previos:
                return None, None
            return float(previos[-1].habitantes), "observado" if previos[-1].anio == anio else "estimado"

    return Poblacion()


def _desde_reportes(con, calc: _Calculo, poblacion):
    # establecimientos que debían reportar cada mes, por parroquia y por cantón
    esperados = {(r.periodo, r.geografia_id): r.n for r in con.execute(text(
        """SELECT m.periodo, g.id AS geografia_id, count(*) AS n
           FROM (SELECT DISTINCT periodo FROM operativo.reporte_alojamiento_mensual) m
           JOIN operativo.establecimiento e
             ON e.participa_desde <= (m.periodo + interval '1 month - 1 day')
            AND (e.participa_hasta IS NULL OR e.participa_hasta >= m.periodo)
           JOIN operativo.geografia p ON p.id = e.parroquia_id
           JOIN operativo.geografia g ON g.id = p.id OR g.id = p.padre_id
           GROUP BY m.periodo, g.id"""))}
    cargas = {r.periodo: r.ids for r in con.execute(text(
        """SELECT periodo, array_agg(DISTINCT carga_id) AS ids
           FROM operativo.reporte_alojamiento_mensual WHERE vigente GROUP BY periodo"""))}

    for a in con.execute(text("SELECT * FROM analitico.v_alojamiento_mensual")).mappings():
        periodo, geo = a["periodo"], a["geografia_id"]
        n, n_ingreso = a["establecimientos_reportantes"], a["establecimientos_con_ingreso"]
        esperado = esperados.get((periodo, geo), 0)
        cobertura = round(_division(n, esperado, 100), 2) if esperado else None
        llegadas, noches = a["llegadas_total"], a["noches_total"]
        noches_nr, llegadas_nr = a["noches_no_residentes"], a["llegadas_no_residentes"]
        hn_disp, hn_ocup = a["habitaciones_noche_disponibles"], a["habitaciones_noche_ocupadas"]
        plazas = a["plazas_cama_noche_disponibles"]
        ingreso = a["ingreso_habitaciones_usd"]

        def agregar(codigo, valor, n_unidades=n, **extra):
            calc.agregar(codigo, periodo, geo, valor, n_unidades, cargas=cargas.get(periodo, ()),
                         cobertura=cobertura, **extra)

        agregar("A1", llegadas, numerador=llegadas)
        agregar("A1", llegadas_nr, dimensiones={"residencia": "no_residente"})
        agregar("A1", llegadas - llegadas_nr, dimensiones={"residencia": "residente"})
        agregar("A2", noches)
        agregar("A2", noches_nr, dimensiones={"residencia": "no_residente"})
        agregar("A2", noches - noches_nr, dimensiones={"residencia": "residente"})
        agregar("A4", _division(noches, llegadas), numerador=noches, denominador=llegadas)
        agregar("A5", _division(noches_nr, noches, 100), numerador=noches_nr, denominador=noches)
        agregar("B2", hn_disp)
        agregar("B3", plazas)
        agregar("B4", _division(hn_ocup, hn_disp, 100), numerador=hn_ocup, denominador=hn_disp)
        agregar("B5", _division(noches, plazas, 100), numerador=noches, denominador=plazas)
        agregar("B6", _division(ingreso, a["hn_ocupadas_con_ingreso"]), n_ingreso,
                numerador=ingreso, denominador=a["hn_ocupadas_con_ingreso"])
        agregar("B7", _division(ingreso, a["hn_disponibles_con_ingreso"]), n_ingreso,
                numerador=ingreso, denominador=a["hn_disponibles_con_ingreso"])
        agregar("Q1", cobertura, numerador=n, denominador=esperado)

        if a["nivel"] == "canton":
            habitantes, bandera = poblacion[(geo, periodo.year)]
            if habitantes:
                agregar("D4", _division(noches, habitantes, 1000), bandera=bandera,
                        fuentes=("plantilla_alojamiento_camara", "inec_poblacion"),
                        numerador=noches, denominador=habitantes)

    # Por categoría de alojamiento (cantón): filtro "categoría" del observatorio
    for a in con.execute(text(
            """SELECT r.periodo, e.categoria, g.padre_id AS canton_id, count(*) AS n,
                      count(r.ingreso_habitaciones_usd) AS n_ingreso,
                      sum(r.llegadas_residentes + r.llegadas_no_residentes) AS llegadas,
                      sum(r.noches_residentes + r.noches_no_residentes) AS noches,
                      sum(r.habitaciones_noche_disponibles) AS hn_disp,
                      sum(r.habitaciones_noche_ocupadas) AS hn_ocup,
                      sum(r.ingreso_habitaciones_usd) AS ingreso,
                      sum(r.habitaciones_noche_ocupadas) FILTER (WHERE r.ingreso_habitaciones_usd IS NOT NULL) AS hn_ocup_ing,
                      sum(r.habitaciones_noche_disponibles) FILTER (WHERE r.ingreso_habitaciones_usd IS NOT NULL) AS hn_disp_ing
               FROM operativo.reporte_alojamiento_mensual r
               JOIN operativo.establecimiento e ON e.id = r.establecimiento_id
               JOIN operativo.geografia g ON g.id = e.parroquia_id
               WHERE r.vigente
               GROUP BY r.periodo, e.categoria, g.padre_id""")).mappings():
        def agregar_categoria(codigo, valor, n_unidades=a["n"], **extra):
            calc.agregar(codigo, a["periodo"], a["canton_id"], valor, n_unidades,
                         dimensiones={"categoria": a["categoria"]}, cargas=cargas.get(a["periodo"], ()), **extra)

        agregar_categoria("A1", a["llegadas"])
        agregar_categoria("A2", a["noches"])
        agregar_categoria("A4", _division(a["noches"], a["llegadas"]), numerador=a["noches"], denominador=a["llegadas"])
        agregar_categoria("B4", _division(a["hn_ocup"], a["hn_disp"], 100), numerador=a["hn_ocup"], denominador=a["hn_disp"])
        agregar_categoria("B6", _division(a["ingreso"], a["hn_ocup_ing"]), a["n_ingreso"],
                          numerador=a["ingreso"], denominador=a["hn_ocup_ing"])
        agregar_categoria("B7", _division(a["ingreso"], a["hn_disp_ing"]), a["n_ingreso"],
                          numerador=a["ingreso"], denominador=a["hn_disp_ing"])


def _desde_fuentes_externas(con, calc: _Calculo, poblacion):
    externas = con.execute(text(
        """SELECT variable, geografia_id, periodo_inicio AS periodo, dimensiones, valor
           FROM operativo.observacion_externa
           WHERE vigente AND variable IN ('catastro_establecimientos', 'hosteleria_plazas',
                                          'hosteleria_establecimientos')""")).mappings().all()

    # B1: alojamientos inscritos en el catastro, por parroquia, cantón y clasificación
    for e in externas:
        if e["variable"] != "catastro_establecimientos" or e["dimensiones"].get("actividad") != "ALOJAMIENTO":
            continue
        clasificacion = e["dimensiones"].get("clasificacion")
        calc.agregar("B1", e["periodo"], e["geografia_id"], float(e["valor"]), int(e["valor"]),
                     dimensiones={"clasificacion": clasificacion} if clasificacion else None,
                     fuentes=("catastro_turistico",), publicable=True)

    # D6: plazas instaladas (base municipal) por cada 100 residentes
    establecimientos = {(e["periodo"], e["geografia_id"]): int(e["valor"]) for e in externas
                        if e["variable"] == "hosteleria_establecimientos" and not e["dimensiones"]}
    for e in externas:
        if e["variable"] != "hosteleria_plazas" or e["dimensiones"]:
            continue
        habitantes, bandera = poblacion[(e["geografia_id"], e["periodo"].year)]
        calc.agregar("D6", e["periodo"], e["geografia_id"], _division(e["valor"], habitantes, 100),
                     establecimientos.get((e["periodo"], e["geografia_id"])), bandera=bandera or "observado",
                     fuentes=("hosteleria_cuenca", "inec_poblacion"), numerador=e["valor"],
                     denominador=habitantes, publicable=True)


def _desde_reportes_complementarios(con, calc: _Calculo):
    """Empleo (D3), accesibilidad y certificaciones (E1, E6) y consumos por noche (E3–E5), a nivel cantonal."""
    for r in con.execute(text("""
            SELECT r.periodo, g.padre_id AS canton, count(*) AS n, sum(r.empleo_total) AS total,
                   sum(r.empleo_estacional) AS estacional
            FROM operativo.reporte_empleo_trimestral r
            JOIN operativo.establecimiento e ON e.id = r.establecimiento_id
            JOIN operativo.geografia g ON g.id = e.parroquia_id
            WHERE r.vigente GROUP BY r.periodo, g.padre_id""")).mappings():
        calc.agregar("D3", r["periodo"], r["canton"], _division(r["estacional"], r["total"], 100), r["n"],
                     numerador=r["estacional"], denominador=r["total"], periodicidad="trimestral",
                     fuentes=("plantilla_empleo_camara",))

    for r in con.execute(text("""
            SELECT r.anio, g.padre_id AS canton, count(*) AS n, sum(r.habitaciones_auditadas) AS auditadas,
                   sum(r.habitaciones_accesibles) AS accesibles,
                   count(*) FILTER (WHERE r.certificacion_vigente_hasta >= make_date(r.anio, 1, 1)) AS certificados
            FROM operativo.reporte_accesibilidad_anual r
            JOIN operativo.establecimiento e ON e.id = r.establecimiento_id
            JOIN operativo.geografia g ON g.id = e.parroquia_id
            WHERE r.vigente GROUP BY r.anio, g.padre_id""")).mappings():
        inicio = date(r["anio"], 1, 1)
        comun = dict(periodicidad="anual", fuentes=("plantilla_accesibilidad_camara",))
        calc.agregar("E1", inicio, r["canton"], _division(r["accesibles"], r["auditadas"], 100), r["n"],
                     numerador=r["accesibles"], denominador=r["auditadas"], **comun)
        calc.agregar("E6", inicio, r["canton"], _division(r["certificados"], r["n"], 100), r["n"],
                     numerador=r["certificados"], denominador=r["n"], **comun)

    # Cada consumo se divide solo por las noches de los establecimientos que reportaron ese consumo
    for r in con.execute(text("""
            SELECT c.periodo, g.padre_id AS canton,
                   count(*) FILTER (WHERE c.agua_m3 IS NOT NULL) AS n_agua, sum(c.agua_m3) AS agua,
                   sum(a.noches_residentes + a.noches_no_residentes) FILTER (WHERE c.agua_m3 IS NOT NULL) AS noches_agua,
                   count(*) FILTER (WHERE c.energia_kwh IS NOT NULL) AS n_energia, sum(c.energia_kwh) AS energia,
                   sum(a.noches_residentes + a.noches_no_residentes) FILTER (WHERE c.energia_kwh IS NOT NULL) AS noches_energia,
                   count(*) FILTER (WHERE c.residuos_kg IS NOT NULL) AS n_residuos, sum(c.residuos_kg) AS residuos,
                   sum(a.noches_residentes + a.noches_no_residentes) FILTER (WHERE c.residuos_kg IS NOT NULL) AS noches_residuos
            FROM operativo.reporte_consumo_mensual c
            JOIN operativo.reporte_alojamiento_mensual a
              ON a.establecimiento_id = c.establecimiento_id AND a.periodo = c.periodo AND a.vigente
            JOIN operativo.establecimiento e ON e.id = c.establecimiento_id
            JOIN operativo.geografia g ON g.id = e.parroquia_id
            WHERE c.vigente GROUP BY c.periodo, g.padre_id""")).mappings():
        for codigo, medida, factor in (("E3", "agua", 1000), ("E4", "energia", 1), ("E5", "residuos", 1)):
            calc.agregar(codigo, r["periodo"], r["canton"], _division(r[medida], r[f"noches_{medida}"], factor),
                         r[f"n_{medida}"], numerador=r[medida], denominador=r[f"noches_{medida}"],
                         fuentes=("plantilla_consumos_camara", "plantilla_alojamiento_camara"))


def recalcular() -> int:
    with transaccion() as con:
        calc = _Calculo(
            versiones=dict(con.execute(text(
                "SELECT codigo, version FROM analitico.indicador WHERE vigente_hasta IS NULL")).all()),
            minimo_publicacion=int(con.execute(text(
                "SELECT valor FROM operativo.parametro WHERE clave = 'min_establecimientos_publicacion'")).scalar()),
            fuentes=dict(con.execute(text("SELECT codigo, id FROM operativo.fuente_datos")).all()),
        )
        poblacion = _poblacion(con)
        _desde_reportes(con, calc, poblacion)
        _desde_fuentes_externas(con, calc, poblacion)
        _desde_reportes_complementarios(con, calc)

        con.execute(text("DELETE FROM analitico.observacion"))
        if calc.filas:
            con.execute(text(
                """INSERT INTO analitico.observacion
                     (indicador_codigo, indicador_version, periodo_inicio, periodo_fin, periodicidad, geografia_id,
                      dimensiones, valor, motivo_no_calculable, numerador, denominador, bandera, n_unidades,
                      cobertura_pct, publicable, fuente_ids, carga_ids)
                   VALUES (:codigo, :version, :ini, :fin, :periodicidad, :geo,
                           CAST(:dims AS jsonb), :valor, :motivo, :num, :den, :bandera, :n,
                           :cobertura, :publicable, :fuentes, :cargas)"""), calc.filas)
        return len(calc.filas)
