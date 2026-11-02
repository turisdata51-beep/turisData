"""Motor de cálculo: fórmulas del manual, confidencialidad, población y fuentes externas.

Escenario: septiembre 2026, 3 hoteles en El Sagrario (EST-01..03, 3 estrellas)
y 1 en San Blas (EST-04, 4 estrellas). Valores elegidos para calcular a mano.
"""
import json
from datetime import date

import pytest
from sqlalchemy import text

from app.nucleo.db import transaccion
from app.servicios.plantillas import importar
from app.servicios.indicadores import recalcular
from conftest import csv_reporte, fila_reporte, observacion, usuario

SEPT = date(2026, 9, 1)


def aprox(esperado):
    """El sistema guarda los indicadores redondeados a 4 decimales."""
    return pytest.approx(esperado, abs=1e-4)


@pytest.fixture
def septiembre():
    importar(csv_reporte(
        fila_reporte("EST-01", habitaciones_noche_ocupadas=300, ingreso_habitaciones_usd=15000),
        fila_reporte("EST-02", habitaciones_noche_ocupadas=450, noches_residentes=350, ingreso_habitaciones_usd=27000),
        fila_reporte("EST-03", habitaciones_noche_ocupadas=150, noches_residentes=100, noches_no_residentes=50,
                     llegadas_residentes=60, llegadas_no_residentes=15, ingreso_habitaciones_usd=""),
        fila_reporte("EST-04", categoria="4 estrellas", parroquia="San Blas", habitaciones_noche_ocupadas=240,
                     noches_residentes=150, noches_no_residentes=100, ingreso_habitaciones_usd=12000),
    ), "septiembre.csv", usuario("analista"))


def valor(codigo, zona="Cuenca", dimensiones=None, periodo=SEPT):
    o = observacion(codigo, periodo, zona, dimensiones)
    return float(o["valor"]) if o and o["valor"] is not None else None


def test_ocupacion_se_calcula_sobre_sumas(septiembre):
    # (300 + 450 + 150 + 240) / (4 × 600) × 100; nunca el promedio de porcentajes
    assert valor("B4") == aprox(1140 / 2400 * 100)


def test_llegadas_pernoctaciones_y_estancia(septiembre):
    llegadas = 150 + 150 + 75 + 150
    noches = 300 + 450 + 150 + 250
    assert valor("A1") == llegadas
    assert valor("A2") == noches
    assert valor("A4") == aprox(noches / llegadas)
    assert valor("A2", dimensiones={"residencia": "no_residente"}) == 100 + 100 + 50 + 100


def test_adr_y_revpar_solo_con_quienes_reportan_ingreso(septiembre):
    ingreso = 15000 + 27000 + 12000           # EST-03 no reporta ingreso
    assert valor("B6") == aprox(ingreso / (300 + 450 + 240))
    assert valor("B7") == aprox(ingreso / (600 * 3))
    assert observacion("B6", SEPT)["n_unidades"] == 3


def test_confidencialidad_por_parroquia(septiembre):
    sagrario, san_blas = observacion("B4", SEPT, "El Sagrario"), observacion("B4", SEPT, "San Blas")
    assert sagrario["publicable"] and sagrario["n_unidades"] == 3
    assert not san_blas["publicable"]       # un solo hotel: se calcula pero no se publica


def test_indicadores_por_categoria(septiembre):
    tres = observacion("B4", SEPT, dimensiones={"categoria": "3 estrellas"})
    cuatro = observacion("B4", SEPT, dimensiones={"categoria": "4 estrellas"})
    assert float(tres["valor"]) == aprox(900 / 1800 * 100) and tres["publicable"]
    assert not cuatro["publicable"]


def test_cobertura_q1_cuenta_hoteles_que_no_reportan():
    importar(csv_reporte(fila_reporte("EST-01"), fila_reporte("EST-02"), fila_reporte("EST-03")),
             "parcial.csv", usuario("analista"))
    assert valor("Q1") == 75.0               # 3 de 4 participantes


def test_d4_usa_la_proyeccion_del_anio_y_la_marca_como_estimada(septiembre):
    with transaccion() as con:
        ejecucion = con.execute(text("""INSERT INTO operativo.ejecucion_extractor (fuente_id, extractor, estado)
            SELECT id, 'prueba', 'ok' FROM operativo.fuente_datos WHERE codigo = 'inec_poblacion' RETURNING id""")).scalar()
        con.execute(text("""INSERT INTO operativo.observacion_externa
            (variable, geografia_id, periodo_inicio, periodo_fin, periodicidad, valor, ejecucion_id)
            SELECT 'inec_poblacion_proyectada', id, '2026-01-01', '2026-12-31', 'anual', 600000, :e
            FROM operativo.geografia WHERE nombre = 'Cuenca'"""), dict(e=ejecucion))
    recalcular()
    d4 = observacion("D4", SEPT)
    assert float(d4["valor"]) == aprox(1150 / 600000 * 1000)
    assert d4["bandera"] == "estimado"


def test_d4_sin_proyeccion_usa_el_censo(septiembre):
    d4 = observacion("D4", SEPT)
    assert float(d4["denominador"]) == 596101  # Censo 2022 (db/003_contenido_sitio.sql)
    assert d4["bandera"] == "estimado"           # el censo no es del año del período


def test_b1_y_d6_desde_fuentes_externas():
    with transaccion() as con:
        ejecucion = con.execute(text("""INSERT INTO operativo.ejecucion_extractor (fuente_id, extractor, estado)
            SELECT id, 'prueba', 'ok' FROM operativo.fuente_datos WHERE codigo = 'catastro_turistico' RETURNING id""")).scalar()
        for variable, zona, dims, val in [
            ("catastro_establecimientos", "Cuenca", {"actividad": "ALOJAMIENTO"}, 372),
            ("catastro_establecimientos", "El Sagrario", {"actividad": "ALOJAMIENTO"}, 86),
            ("catastro_establecimientos", "Cuenca", {"actividad": "ALIMENTOS Y BEBIDAS"}, 893),
            ("hosteleria_plazas", "Cuenca", {}, 9736),
            ("hosteleria_establecimientos", "Cuenca", {}, 290),
        ]:
            con.execute(text("""INSERT INTO operativo.observacion_externa
                (variable, geografia_id, periodo_inicio, periodo_fin, periodicidad, dimensiones, valor, ejecucion_id)
                SELECT :v, id, '2025-04-01', '2025-04-30', 'mensual', CAST(:d AS jsonb), :val, :e
                FROM operativo.geografia WHERE nombre = :z"""),
                dict(v=variable, z=zona, d=json.dumps(dims), val=val, e=ejecucion))
    recalcular()
    abril = date(2025, 4, 1)
    assert valor("B1", periodo=abril) == 372
    assert valor("B1", "El Sagrario", periodo=abril) == 86
    d6 = observacion("D6", abril)
    assert float(d6["valor"]) == aprox(9736 / 596101 * 100)  # sin proyección 2025: censo
    assert d6["publicable"] and d6["n_unidades"] == 290


def test_recalcular_no_deja_valores_de_versiones_cerradas(septiembre):
    with transaccion() as con:
        vigentes = dict(con.execute(text(
            "SELECT codigo, version FROM analitico.indicador WHERE vigente_hasta IS NULL")).all())
        usadas = con.execute(text(
            "SELECT DISTINCT indicador_codigo, indicador_version FROM analitico.observacion")).all()
    assert all(vigentes[c] == v for c, v in usadas)
