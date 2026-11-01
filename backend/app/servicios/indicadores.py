"""Motor de cálculo: recalcula analitico.observacion a partir de los reportes vigentes.

Los KPI se calculan sobre sumas (vista analitico.v_alojamiento_mensual), nunca
promediando porcentajes de cada hotel. Un valor con menos establecimientos que el
mínimo de confidencialidad se guarda con publicable = false.
"""
import json

from sqlalchemy import text

from ..nucleo.db import transaccion


def _division(numerador, denominador, factor=1):
    if numerador is None or not denominador:
        return None
    return float(numerador) / float(denominador) * factor


def recalcular() -> int:
    with transaccion() as con:
        minimo = int(con.execute(text(
            "SELECT valor FROM operativo.parametro WHERE clave = 'min_establecimientos_publicacion'")).scalar())
        versiones = dict(con.execute(text(
            "SELECT codigo, version FROM analitico.indicador WHERE vigente_hasta IS NULL")).all())
        fuente_hoteles = con.execute(text(
            "SELECT id FROM operativo.fuente_datos WHERE codigo = 'plantilla_alojamiento_camara'")).scalar()
        fuente_inec = con.execute(text(
            "SELECT id FROM operativo.fuente_datos WHERE codigo = 'inec_poblacion'")).scalar()
        poblacion = con.execute(text(
            """SELECT p.geografia_id, p.anio, p.habitantes FROM operativo.poblacion p
               ORDER BY p.geografia_id, p.anio""")).all()
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
        cargas = {r.periodo: list(r.ids) for r in con.execute(text(
            """SELECT periodo, array_agg(DISTINCT carga_id) AS ids
               FROM operativo.reporte_alojamiento_mensual WHERE vigente GROUP BY periodo"""))}
        agregados = con.execute(text("SELECT * FROM analitico.v_alojamiento_mensual")).mappings().all()

        filas = []

        def agregar(codigo, a, valor, n, dimensiones=None, bandera="observado", fuentes=None, motivo=None,
                    numerador=None, denominador=None, cobertura=None):
            if codigo not in versiones:
                return
            filas.append(dict(
                codigo=codigo, version=versiones[codigo], ini=a["periodo"], geo=a["geografia_id"],
                dims=json.dumps(dimensiones or {}, ensure_ascii=False),
                valor=None if valor is None else round(valor, 4),
                motivo=(motivo or "denominador cero o sin datos") if valor is None else None,
                num=numerador, den=denominador, bandera=bandera, n=n, cobertura=cobertura,
                publicable=valor is not None and n >= minimo,
                fuentes=fuentes or [fuente_hoteles], cargas=cargas.get(a["periodo"], [])))

        for a in agregados:
            n = a["establecimientos_reportantes"]
            n_ing = a["establecimientos_con_ingreso"]
            esp = esperados.get((a["periodo"], a["geografia_id"]), 0)
            cobertura = round(_division(n, esp, 100), 2) if esp else None
            base = dict(cobertura=cobertura)
            llegadas, noches = a["llegadas_total"], a["noches_total"]
            nnr, lnr = a["noches_no_residentes"], a["llegadas_no_residentes"]

            agregar("A1", a, llegadas, n, numerador=llegadas, **base)
            agregar("A1", a, lnr, n, {"residencia": "no_residente"}, **base)
            agregar("A1", a, llegadas - lnr, n, {"residencia": "residente"}, **base)
            agregar("A2", a, noches, n, **base)
            agregar("A2", a, nnr, n, {"residencia": "no_residente"}, **base)
            agregar("A2", a, noches - nnr, n, {"residencia": "residente"}, **base)
            agregar("A4", a, _division(noches, llegadas), n, numerador=noches, denominador=llegadas, **base)
            agregar("A5", a, _division(nnr, noches, 100), n, numerador=nnr, denominador=noches, **base)
            agregar("B1", a, n, n, **base)
            agregar("B2", a, a["habitaciones_noche_disponibles"], n, **base)
            agregar("B3", a, a["plazas_cama_noche_disponibles"], n, **base)
            agregar("B4", a, _division(a["habitaciones_noche_ocupadas"], a["habitaciones_noche_disponibles"], 100), n,
                    numerador=a["habitaciones_noche_ocupadas"], denominador=a["habitaciones_noche_disponibles"], **base)
            agregar("B5", a, _division(noches, a["plazas_cama_noche_disponibles"], 100), n,
                    numerador=noches, denominador=a["plazas_cama_noche_disponibles"], **base)
            agregar("B6", a, _division(a["ingreso_habitaciones_usd"], a["hn_ocupadas_con_ingreso"]), n_ing,
                    numerador=a["ingreso_habitaciones_usd"], denominador=a["hn_ocupadas_con_ingreso"], **base)
            agregar("B7", a, _division(a["ingreso_habitaciones_usd"], a["hn_disponibles_con_ingreso"]), n_ing,
                    numerador=a["ingreso_habitaciones_usd"], denominador=a["hn_disponibles_con_ingreso"], **base)
            agregar("Q1", a, cobertura, n, numerador=n, denominador=esp, **base)

            if a["nivel"] == "canton":
                anio = a["periodo"].year
                candidatas = [p for p in poblacion if p.geografia_id == a["geografia_id"] and p.anio <= anio]
                if candidatas:
                    pob = candidatas[-1]
                    agregar("D4", a, _division(noches, pob.habitantes, 1000), n,
                            bandera="observado" if pob.anio == anio else "estimado",
                            fuentes=[fuente_hoteles, fuente_inec], numerador=noches, denominador=pob.habitantes, **base)

        con.execute(text("DELETE FROM analitico.observacion"))
        if filas:
            con.execute(text(
                """INSERT INTO analitico.observacion
                     (indicador_codigo, indicador_version, periodo_inicio, periodo_fin, periodicidad, geografia_id,
                      dimensiones, valor, motivo_no_calculable, numerador, denominador, bandera, n_unidades,
                      cobertura_pct, publicable, fuente_ids, carga_ids)
                   VALUES (:codigo, :version, :ini, (:ini + interval '1 month - 1 day')::date, 'mensual', :geo,
                           CAST(:dims AS jsonb), :valor, :motivo, :num, :den, :bandera, :n,
                           :cobertura, :publicable, :fuentes, :cargas)"""), filas)
        return len(filas)
