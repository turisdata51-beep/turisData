"""Funciones puras: normalización, fechas en nombres de archivo, lectura de cada fuente y seguridad."""
import json
from datetime import date

import pytest

from app.extractores.base import clave_geografica
from app.extractores.catastro_turistico import CatastroTuristico
from app.extractores.ckan import fecha_en_nombre
from app.extractores.hosteleria_cuenca import HosteleriaCuenca, _entero
from app.extractores.inec_poblacion import InecPoblacion
from app.extractores.sri_ventas import SriVentas
from app.nucleo.seguridad import hash_contrasena, verificar_contrasena
from app.servicios.indicadores import _division


@pytest.mark.parametrize("a, b", [
    ("Huayna Cápac", "HUAYNACÁPAC"),
    ("El Valle", "VALLE"),
    ("Gil Ramírez Dávalos", "gil ramirez davalos"),
    ("San Sebastián", "SAN SEBASTIAN"),
])
def test_clave_geografica_iguala_escrituras_distintas(a, b):
    assert clave_geografica(a) == clave_geografica(b)


def test_clave_geografica_distingue_parroquias():
    assert clave_geografica("San Blas") != clave_geografica("San Joaquín")


@pytest.mark.parametrize("nombre, esperado", [
    ("1era quincena Febrero Catastro Nacional 2025 - BANECUADOR.xlsx", date(2025, 2, 1)),
    ("GADCuenca_Hosteleria_2025Abril.csv", date(2025, 4, 1)),
    ("Catastro setiembre 2024", date(2024, 9, 1)),
    ("archivo_sin_fecha.csv", None),
])
def test_fecha_en_nombre(nombre, esperado):
    assert fecha_en_nombre(nombre) == esperado


def test_division_protege_denominador_cero():
    assert _division(10, 0) is None
    assert _division(None, 5) is None
    assert _division(1, 4, 100) == 25.0


def test_contrasena_hash_y_verificacion():
    guardado = hash_contrasena("una-clave-segura")
    assert guardado.startswith("scrypt$")
    assert "una-clave-segura" not in guardado
    assert verificar_contrasena("una-clave-segura", guardado)
    assert not verificar_contrasena("otra-clave", guardado)
    assert not verificar_contrasena("una-clave-segura", "formato-invalido")


def test_hash_usa_sal_distinta_cada_vez():
    assert hash_contrasena("misma") != hash_contrasena("misma")


# --- Lectura de archivos del SRI (el formato cambia entre años) -------------------------------

SRI_2019 = ("AÑO|MES|CODIGO_SECTOR_N1|PROVINCIA|CANTON|VENTAS_NETAS_TARIFA_12|TOTAL_VENTA\n"
            "2019|1|I|AZUAY|CUENCA|10,5|1000,25\n"
            "2019|1|G|AZUAY|CUENCA|1|999\n"
            "2019|2|I|PICHINCHA|QUITO|1|5000\n").encode("latin-1")
SRI_2025 = ("﻿AÑO,MES,CODIGO_SECTOR_N1,PROVINCIA,CANTON,VENTAS_NETAS_TARIFA_GRAVADA,TOTAL_VENTAS\n"
            "2025,3,I,AZUAY,CUENCA,1.5,2500.75\n").encode("utf-8")


def test_sri_lee_formato_antiguo_con_barras_y_latin1():
    assert list(SriVentas._filas_cuenca(SRI_2019)) == [(1, 1000.25)]


def test_sri_lee_formato_nuevo_con_comas_y_utf8():
    assert list(SriVentas._filas_cuenca(SRI_2025)) == [(3, 2500.75)]


def test_sri_interpreta_meses_con_su_ultimo_dia():
    datos = SriVentas.__new__(SriVentas).interpretar(b"ANIO|MES|TOTAL_VENTAS\n2024|02|123.5\n")
    assert len(datos) == 1
    assert datos[0].periodo_inicio == date(2024, 2, 1)
    assert datos[0].periodo_fin == date(2024, 2, 29)  # año bisiesto
    assert datos[0].valor == 123.5


# --- Catastro, hostelería e INEC ----------------------------------------------------------------

def test_catastro_agrega_por_parroquia_actividad_y_clasificacion():
    resumen = {"corte": "2025-02-01", "archivo": "x", "conteos": [
        ["El Sagrario", "ALOJAMIENTO", "HOTEL", 3],
        ["El Sagrario", "ALOJAMIENTO", "HOSTAL", 2],
        ["San Blas", "ALOJAMIENTO", "HOTEL", 1],
        ["El Sagrario", "ALIMENTOS Y BEBIDAS", "RESTAURANTE", 7],
    ]}
    datos = CatastroTuristico.__new__(CatastroTuristico).interpretar(json.dumps(resumen).encode())
    valor = {(d.geografia, json.dumps(d.dimensiones, sort_keys=True)): d.valor for d in datos}
    assert valor[("El Sagrario", '{"actividad": "ALOJAMIENTO"}')] == 5
    assert valor[("Cuenca", '{"actividad": "ALOJAMIENTO"}')] == 6
    assert valor[("Cuenca", '{"actividad": "ALOJAMIENTO", "clasificacion": "HOTEL"}')] == 4
    assert valor[("Cuenca", '{"actividad": "ALIMENTOS Y BEBIDAS"}')] == 7
    assert all(d.periodo_fin == date(2025, 2, 28) for d in datos)


def test_hosteleria_tolera_numeros_mal_escritos():
    assert _entero("12") == 12
    assert _entero("12,0") == 12
    assert _entero("ND") is None


def test_hosteleria_separa_total_y_tipos():
    resumen = {"corte": "2025-04-01", "archivo": "x", "totales": {
        "TOTAL": {"establecimientos": 2, "habitaciones": 30, "plazas": 60},
        "HOTEL": {"establecimientos": 1, "habitaciones": 20, "plazas": 40}}}
    datos = HosteleriaCuenca.__new__(HosteleriaCuenca).interpretar(json.dumps(resumen).encode())
    plazas_total = next(d for d in datos if d.variable == "hosteleria_plazas" and not d.dimensiones)
    plazas_hotel = next(d for d in datos if d.variable == "hosteleria_plazas" and d.dimensiones == {"tipo": "HOTEL"})
    assert (plazas_total.valor, plazas_hotel.valor) == (60, 40)
    assert len(datos) == 6


def test_inec_genera_un_dato_anual_por_anio():
    datos = InecPoblacion.__new__(InecPoblacion).interpretar(b'{"2025": 624053, "2026": 628740}')
    assert [(d.periodo_inicio, d.periodo_fin, d.valor, d.periodicidad) for d in datos] == [
        (date(2025, 1, 1), date(2025, 12, 31), 624053, "anual"),
        (date(2026, 1, 1), date(2026, 12, 31), 628740, "anual"),
    ]
