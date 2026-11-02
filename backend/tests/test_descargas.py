"""Scraping completo de cada fuente contra sitios simulados (misma estructura que los reales, sin internet).

Cada prueba reemplaza Extractor.obtener por un diccionario URL -> contenido y ejecuta
descargar() + interpretar(), es decir, todo el camino: leer la página, encontrar el
archivo correcto, descargarlo y extraer los datos de Cuenca.
"""
import io
import json
from datetime import date

import pytest
from openpyxl import Workbook

from app.extractores import ckan
from app.extractores.catastro_turistico import CatastroTuristico
from app.extractores.hosteleria_cuenca import HosteleriaCuenca
from app.extractores.inec_poblacion import InecPoblacion
from app.extractores.sri_ventas import SriVentas


class Respuesta:
    def __init__(self, contenido):
        self.content = contenido if isinstance(contenido, bytes) else contenido.encode("utf-8")
        self.text = self.content.decode("utf-8", errors="replace")

    def json(self):
        return json.loads(self.content)


def sitio_simulado(extractor, paginas: dict):
    """Hace que el extractor 'navegue' en un sitio falso; falla si pide una URL desconocida."""
    def obtener(url, **_):
        if url not in paginas:
            raise AssertionError(f"El extractor pidió una URL inesperada: {url}")
        return Respuesta(paginas[url])
    extractor.obtener = obtener
    return extractor


def xlsx(filas: list[list], hoja="Hoja1") -> bytes:
    libro = Workbook()
    ws = libro.active
    ws.title = hoja
    for f in filas:
        ws.append(f)
    salida = io.BytesIO()
    libro.save(salida)
    return salida.getvalue()


def pagina_ckan(base: str, paquete: str, recursos: dict[str, str]) -> dict:
    """Página del conjunto + página de cada recurso con su enlace de descarga (como CKAN)."""
    enlaces, paginas = [], {}
    for i, nombre in enumerate(recursos):
        rid = f"00000000-0000-0000-0000-00000000000{i}"
        ruta = f"/dataset/{paquete}/resource/{rid}"
        enlaces.append(f'<li class="resource-item"><a class="heading" href="{ruta}" title="{nombre}">{nombre}</a></li>')
        paginas[f"{base}{ruta}"] = f'<a href="{base}/dataset/x/resource/{rid}/download/{nombre}">Descargar</a>'
        paginas[f"{base}/dataset/x/resource/{rid}/download/{nombre}"] = recursos[nombre]
    paginas[f"{base}/dataset/{paquete}"] = "<ul>" + "".join(enlaces) + "</ul>"
    return paginas


# --- SRI ------------------------------------------------------------------------------------

def test_sri_encuentra_los_archivos_en_la_pagina_y_filtra_cuenca():
    base = "https://www.sri.gob.ec"
    v2025 = "﻿AÑO,MES,CODIGO_SECTOR_N1,PROVINCIA,CANTON,TOTAL_VENTAS\n2025,12,I,AZUAY,CUENCA,3000.5\n2025,12,I,AZUAY,GUALACEO,10\n"
    v2026 = ("AÑO|MES|CODIGO_SECTOR_N1|PROVINCIA|CANTON|TOTAL_VENTAS\n2026|1|I|AZUAY|CUENCA|1500,25\n"
             "2026|1|G|AZUAY|CUENCA|99\n").encode("latin-1")
    extractor = sitio_simulado(SriVentas(), {
        f"{base}/datasets": f'<a href="{base}/d/sri_ventas_2025.csv">2025</a> <a href="{base}/d/sri_ventas_2026.csv ">2026</a>',
        f"{base}/d/sri_ventas_2025.csv": v2025.encode("utf-8"),
        f"{base}/d/sri_ventas_2026.csv": v2026,
    })
    datos = extractor.interpretar(extractor.descargar())
    assert [(d.periodo_inicio, d.valor) for d in datos] == [(date(2025, 12, 1), 3000.5), (date(2026, 1, 1), 1500.25)]


def test_sri_avisa_si_no_encuentra_cuenca():
    extractor = sitio_simulado(SriVentas(), {
        "https://www.sri.gob.ec/datasets": '<a href="https://x/sri_ventas_2026.csv">2026</a>',
        "https://x/sri_ventas_2026.csv": b"ANIO|MES|CODIGO_SECTOR_N1|PROVINCIA|CANTON|TOTAL_VENTAS\n2026|1|I|LOJA|LOJA|5\n",
    })
    with pytest.raises(ValueError, match="No se encontraron filas de Cuenca"):
        extractor.descargar()


# --- Portales CKAN ----------------------------------------------------------------------------

def test_ckan_elige_el_archivo_mas_reciente_del_formato_pedido():
    base = "https://portal.test"
    extractor = sitio_simulado(HosteleriaCuenca(), pagina_ckan(base, "hosteleria", {
        "Hosteleria_2022Septiembre.csv": "a", "Hosteleria_2025Abril.csv": "b", "Hosteleria_DD_2025Abril.ods": "c"}))
    recurso = ckan.mas_reciente(extractor, f"{base}/dataset/hosteleria", ".csv")
    assert (recurso.nombre, recurso.corte) == ("Hosteleria_2025Abril.csv", date(2025, 4, 1))


def test_hosteleria_suma_capacidad_sin_guardar_datos_personales():
    csv = ("tipo;nombre;telefono 1;nro_habitaciones;responsable;nro_plazas;email\n"
           "HOTEL;Hotel A;0999;20;JUAN PEREZ;40;a@b.com\n"
           "HOSTAL;Hostal B;0988;ND;ANA LOPEZ;12;c@d.com\n")
    extractor = sitio_simulado(HosteleriaCuenca(), pagina_ckan(
        "https://cuencaendatos.cuenca.gob.ec", "hosteleria", {"GADCuenca_Hosteleria_2025Abril.csv": csv}))
    contenido = extractor.descargar()
    assert b"JUAN" not in contenido and b"@" not in contenido   # solo totales agregados
    totales = json.loads(contenido)["totales"]
    assert totales["TOTAL"] == {"establecimientos": 2, "habitaciones": 20, "plazas": 52}
    assert totales["HOSTAL"]["habitaciones"] == 0                # "ND" no se suma


def test_catastro_filtra_cuenca_desde_el_excel():
    filas = [
        ["RUC", "Nombre Comercial", "Actividad / Modalidad", "Clasificación", "Representante Legal",
         "Provincia", "Cantón", "Parroquia"],
        ["0101", "Hotel A", "ALOJAMIENTO", "HOTEL", "PERSONA UNO", "AZUAY", "CUENCA", "EL SAGRARIO"],
        ["0102", "Hostal B", "ALOJAMIENTO", "HOSTAL", "PERSONA DOS", "AZUAY", "CUENCA", "HUAYNACÁPAC"],
        ["0103", "Hotel C", "ALOJAMIENTO", "HOTEL", "PERSONA TRES", "AZUAY", "GUALACEO", "GUALACEO"],
    ]
    extractor = sitio_simulado(CatastroTuristico(), pagina_ckan(
        "https://www.datosabiertos.gob.ec", "catastro-turistico-total",
        {"1era quincena Febrero Catastro Nacional 2025.xlsx": xlsx(filas)}))
    contenido = extractor.descargar()
    assert b"PERSONA" not in contenido and b"0101" not in contenido
    datos = extractor.interpretar(contenido)
    total = next(d for d in datos if d.geografia == "Cuenca" and d.dimensiones == {"actividad": "ALOJAMIENTO"})
    assert total.valor == 2 and total.periodo_inicio == date(2025, 2, 1)


# --- INEC -------------------------------------------------------------------------------------

def test_inec_lee_la_hoja_cantonal():
    anios = list(range(2010, 2036))
    fila_anios = ["", "", "", "", "", ""] + [x for a in anios for x in (str(a), "", "")]
    fila_total = ["01", "Azuay", "0101", "Cuenca", "Total", ""] + [x for a in anios for x in (1, 1, 500000 + a)]
    otra = ["01", "Azuay", "0102", "Girón", "Total", ""] + [9] * (len(anios) * 3)
    extractor = sitio_simulado(InecPoblacion(), {InecPoblacion.url: xlsx([["Tabla 3.2"], fila_anios, otra, fila_total], hoja="3.2")})
    poblacion = json.loads(extractor.descargar())
    assert poblacion["2026"] == 502026 and len(poblacion) == 26


def test_inec_avisa_si_cambia_el_formato():
    extractor = sitio_simulado(InecPoblacion(), {InecPoblacion.url: xlsx([["otra cosa"]], hoja="Resumen")})
    with pytest.raises(ValueError, match="hoja 3.2"):
        extractor.descargar()
