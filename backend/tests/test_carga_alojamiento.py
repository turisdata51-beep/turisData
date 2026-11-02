"""Carga del reporte mensual: validación fila por fila, reemplazo con historial y permisos del asociado."""
import io

from openpyxl import Workbook
from sqlalchemy import text

from app.nucleo.db import transaccion
from app.servicios.plantillas import PLANTILLAS, importar

COLUMNAS = [c.nombre for c in PLANTILLAS["alojamiento"].columnas]
from conftest import csv_reporte, fila_reporte, usuario


def reportes(vigente=None):
    filtro = "" if vigente is None else f"WHERE vigente = {str(vigente).lower()}"
    with transaccion() as con:
        return [dict(r) for r in con.execute(text(
            f"SELECT * FROM operativo.reporte_alojamiento_mensual {filtro} ORDER BY id")).mappings()]


def mensajes(resultado):
    return [(e["fila"], e["campo"], e["mensaje"]) for e in resultado["errores"] if e["severidad"] == "error"]


def test_carga_valida_se_publica():
    r = importar(csv_reporte(fila_reporte("EST-01"), fila_reporte("EST-02")), "ok.csv", usuario("analista"))
    assert r["estado"] == "publicada"
    assert (r["registros_recibidos"], r["registros_validos"], r["registros_rechazados"]) == (2, 2, 0)
    assert len(reportes()) == 2


def test_carga_xlsx_con_la_hoja_datos():
    libro = Workbook()
    hoja = libro.active
    hoja.title = "Datos"
    hoja.append(COLUMNAS)
    hoja.append([fila_reporte()[c] for c in COLUMNAS])
    archivo = io.BytesIO()
    libro.save(archivo)
    r = importar(archivo.getvalue(), "reporte.xlsx", usuario("analista"))
    assert r["estado"] == "publicada"
    assert reportes()[0]["habitaciones_noche_ocupadas"] == 300


def test_filas_invalidas_se_rechazan_y_las_validas_entran():
    r = importar(csv_reporte(
        fila_reporte("EST-01"),
        fila_reporte("EST-02", habitaciones_noche_ocupadas=700),           # más ocupadas que disponibles
        fila_reporte("NO-EXISTE"),                                         # código desconocido
        fila_reporte("EST-03", dias_operacion=31),                         # septiembre tiene 30 días
        fila_reporte("EST-04", periodo="2026-13"),                         # mes inválido
    ), "mixto.csv", usuario("analista"))
    assert r["estado"] == "con_errores"
    assert (r["registros_validos"], r["registros_rechazados"]) == (1, 4)
    errores = mensajes(r)
    assert (3, "habitaciones_noche_ocupadas", "Las habitaciones ocupadas superan las disponibles") in errores
    assert (4, "codigo_establecimiento", "Código no registrado en la Cámara") in errores
    assert (5, "dias_operacion", "El mes tiene 30 días") in errores
    assert (6, "periodo", "Use el formato AAAA-MM") in errores


def test_reglas_de_consistencia_de_capacidad():
    r = importar(csv_reporte(
        fila_reporte("EST-01", habitaciones_noche_disponibles=700),        # 20 habitaciones × 30 días = 600
        fila_reporte("EST-02", noches_residentes=1500),                    # más noches que plazas
        fila_reporte("EST-03", habitaciones_noche_ocupadas=0),             # noches sin habitaciones ocupadas
        fila_reporte("EST-04", habitaciones_noche_ocupadas=10.5),          # decimal en campo entero
    ), "capacidad.csv", usuario("analista"))
    assert r["estado"] == "rechazada"
    campos = {campo for _, campo, _ in mensajes(r)}
    assert {"habitaciones_noche_disponibles", "noches_residentes", "habitaciones_noche_ocupadas"} <= campos


def test_fila_repetida_en_el_mismo_archivo():
    r = importar(csv_reporte(fila_reporte("EST-01"), fila_reporte("EST-01")), "dup.csv", usuario("analista"))
    assert r["registros_validos"] == 1
    assert any("repetida" in m for *_, m in mensajes(r))


def test_reenvio_reemplaza_y_conserva_historial():
    importar(csv_reporte(fila_reporte("EST-01", habitaciones_noche_ocupadas=300)), "v1.csv", usuario("analista"))
    importar(csv_reporte(fila_reporte("EST-01", habitaciones_noche_ocupadas=450, noches_residentes=300)),
             "v2.csv", usuario("analista"))
    todos = reportes()
    assert len(todos) == 2
    assert [r["vigente"] for r in todos] == [False, True]
    assert reportes(vigente=True)[0]["habitaciones_noche_ocupadas"] == 450


def test_mismo_archivo_dos_veces_se_rechaza():
    archivo = csv_reporte(fila_reporte())
    importar(archivo, "a.csv", usuario("analista"))
    r = importar(archivo, "a.csv", usuario("analista"))
    assert r["estado"] == "rechazada"
    assert "ya se cargó" in r["errores"][0]["mensaje"]


def test_archivo_sin_las_columnas_de_la_plantilla():
    r = importar(b"periodo,codigo_establecimiento\n2026-09,EST-01\n", "corto.csv", usuario("analista"))
    assert r["estado"] == "rechazada"
    assert r["errores"][0]["mensaje"].startswith("Faltan columnas de la plantilla")


def test_formato_no_soportado():
    r = importar(b"%PDF-1.4", "reporte.pdf", usuario("analista"))
    assert r["estado"] == "rechazada"
    assert "Formato no soportado" in r["errores"][0]["mensaje"]


def test_asociado_solo_reporta_su_establecimiento():
    asociado = usuario("asociado")  # ligado a EST-01
    r = importar(csv_reporte(fila_reporte("EST-01"), fila_reporte("EST-02")), "hotel.csv", asociado)
    assert r["registros_validos"] == 1
    assert any("propio establecimiento" in m for *_, m in mensajes(r))


def test_datos_que_no_coinciden_con_el_padron_son_advertencia():
    r = importar(csv_reporte(fila_reporte("EST-01", categoria="5 estrellas")), "adv.csv", usuario("analista"))
    assert r["estado"] == "publicada"
    advertencias = [e for e in r["errores"] if e["severidad"] == "advertencia"]
    assert advertencias and advertencias[0]["campo"] == "categoria"


def test_ingreso_es_opcional():
    r = importar(csv_reporte(fila_reporte(ingreso_habitaciones_usd="")), "sin_ingreso.csv", usuario("analista"))
    assert r["estado"] == "publicada"
    assert reportes()[0]["ingreso_habitaciones_usd"] is None
