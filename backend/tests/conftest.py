"""Configuración común de las pruebas.

Crea una base de datos aparte (observatorio_pruebas) desde los scripts de db/,
así las pruebas nunca tocan los datos de desarrollo. Antes de importar la app se
fijan las variables de entorno para que use esa base y no lance el programador
de extracciones.

Requiere PostgreSQL accesible con un usuario que pueda crear bases. Por defecto
usa el contenedor de docker-compose; en otro entorno, definir PRUEBAS_DB_ADMIN.
"""
import csv
import io
import os
from datetime import date
from pathlib import Path

import psycopg
import pytest

BACKEND = Path(__file__).resolve().parents[1]
SCRIPTS_SQL = BACKEND.parent / "db"
URL_ADMIN = os.environ.get("PRUEBAS_DB_ADMIN", "postgresql://observatorio:observatorio_dev@localhost:5433/postgres")
BASE = "observatorio_pruebas"
URL_BASE = URL_ADMIN.rsplit("/", 1)[0] + f"/{BASE}"


def _crear_base():
    with psycopg.connect(URL_ADMIN, autocommit=True) as con:
        con.execute(f"DROP DATABASE IF EXISTS {BASE} WITH (FORCE)")
        con.execute(f"CREATE DATABASE {BASE}")
    with psycopg.connect(URL_BASE, autocommit=True) as con:
        for script in sorted(SCRIPTS_SQL.glob("*.sql")):
            con.execute(script.read_text(encoding="utf-8"))


_crear_base()
os.environ.update(
    DATABASE_URL=URL_BASE.replace("postgresql://", "postgresql+psycopg://"),
    JWT_SECRET="clave-de-pruebas-que-no-se-usa-en-ningun-otro-lugar",
    EXTRACCION_AUTOMATICA="0",
    ADMIN_CORREO="admin@pruebas.test",
    ADMIN_CONTRASENA="AdminPruebas123",
)

from sqlalchemy import text  # noqa: E402  (después de fijar el entorno)

from app.nucleo.db import transaccion  # noqa: E402
from app.nucleo.seguridad import hash_contrasena  # noqa: E402
from app.servicios.plantillas import PLANTILLAS  # noqa: E402
from app.servicios.diccionario import sincronizar  # noqa: E402

sincronizar()

CONTRASENA = "ClaveDePrueba123"
TABLAS_DE_DATOS = """operativo.reporte_alojamiento_mensual, operativo.carga_error, operativo.carga_datos,
    operativo.establecimiento, operativo.usuario, operativo.auditoria, operativo.observacion_externa,
    operativo.ejecucion_extractor, analitico.observacion"""

# (código, parroquia, categoría): 3 hoteles en El Sagrario y 1 en San Blas
ESTABLECIMIENTOS = [
    ("EST-01", "El Sagrario", "3 estrellas"),
    ("EST-02", "El Sagrario", "3 estrellas"),
    ("EST-03", "El Sagrario", "3 estrellas"),
    ("EST-04", "San Blas", "4 estrellas"),
]


@pytest.fixture(autouse=True)
def base_limpia():
    """Cada prueba arranca con 4 establecimientos, 4 usuarios (uno por rol) y sin reportes."""
    with transaccion() as con:
        con.execute(text(f"TRUNCATE {TABLAS_DE_DATOS} RESTART IDENTITY CASCADE"))
        for codigo, parroquia, categoria in ESTABLECIMIENTOS:
            con.execute(text("""
                INSERT INTO operativo.establecimiento
                  (codigo_camara, nombre_comercial, tipo_alojamiento, categoria, parroquia_id, participa_desde)
                SELECT :c, 'Hotel ' || :c, 'Hotel', :cat, id, '2025-01-01'
                FROM operativo.geografia WHERE nombre = :p"""), dict(c=codigo, cat=categoria, p=parroquia))
        clave = hash_contrasena(CONTRASENA)
        for rol in ("administrador", "analista", "consulta", "asociado"):
            con.execute(text("""
                INSERT INTO operativo.usuario (correo, nombre, hash_contrasena, rol, establecimiento_id)
                VALUES (:correo, :nombre, :h, :rol,
                        CASE WHEN :rol = 'asociado'
                             THEN (SELECT id FROM operativo.establecimiento WHERE codigo_camara = 'EST-01') END)"""),
                dict(correo=f"{rol}@pruebas.test", nombre=rol.title(), h=clave, rol=rol))
    yield


def usuario(rol: str) -> dict:
    with transaccion() as con:
        return dict(con.execute(text("SELECT * FROM operativo.usuario WHERE rol = :r"), dict(r=rol)).mappings().one())


def fila_reporte(codigo="EST-01", periodo="2026-09", **cambios) -> dict:
    """Fila válida de la plantilla v1 (septiembre: 30 días). Los cambios reemplazan valores."""
    datos = dict(
        periodo=periodo, codigo_establecimiento=codigo, tipo_alojamiento="Hotel", categoria="3 estrellas",
        parroquia="El Sagrario", habitaciones_instaladas=20, plazas_instaladas=40, dias_operacion=30,
        habitaciones_noche_disponibles=600, habitaciones_noche_ocupadas=300, plazas_cama_noche_disponibles=1200,
        llegadas_residentes=100, llegadas_no_residentes=50, noches_residentes=200, noches_no_residentes=100,
        ingreso_habitaciones_usd=15000, observaciones="")
    datos.update(cambios)
    return datos


def csv_reporte(*filas: dict) -> bytes:
    salida = io.StringIO()
    columnas = [c.nombre for c in PLANTILLAS["alojamiento"].columnas]
    escritor = csv.DictWriter(salida, fieldnames=columnas)
    escritor.writeheader()
    for f in filas:
        escritor.writerow({c: f.get(c, "") for c in columnas})
    return salida.getvalue().encode("utf-8")


def observacion(codigo: str, periodo: date, zona="Cuenca", dimensiones=None) -> dict | None:
    import json
    with transaccion() as con:
        r = con.execute(text("""
            SELECT o.* FROM analitico.observacion o JOIN operativo.geografia g ON g.id = o.geografia_id
            WHERE o.indicador_codigo = :c AND o.periodo_inicio = :p AND g.nombre = :z
              AND o.dimensiones = CAST(:d AS jsonb)"""),
            dict(c=codigo, p=periodo, z=zona, d=json.dumps(dimensiones or {}, ensure_ascii=False))).mappings().first()
    return dict(r) if r else None
