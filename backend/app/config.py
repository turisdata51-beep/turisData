"""Configuración leída de variables de entorno (archivo backend/.env en desarrollo)."""
import os
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]


def _cargar_env():
    archivo = RAIZ / "backend" / ".env"
    if not archivo.exists():
        return
    for linea in archivo.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if linea and not linea.startswith("#") and "=" in linea:
            clave, valor = linea.split("=", 1)
            os.environ.setdefault(clave.strip(), valor.strip())


_cargar_env()

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql+psycopg://observatorio:observatorio_dev@localhost:5433/observatorio")
JWT_SECRET = os.environ.get("JWT_SECRET", "")
JWT_HORAS = int(os.environ.get("JWT_HORAS", "8"))
CORS_ORIGENES = os.environ.get("CORS_ORIGENES", "http://localhost:5173").split(",")
DICCIONARIO = RAIZ / "docs" / "diccionario_indicadores.yaml"
PLANTILLA_XLSX = RAIZ / "plantillas" / "reporte_mensual_alojamiento_v1.xlsx"

if not JWT_SECRET:
    raise RuntimeError("Falta JWT_SECRET en backend/.env (ver backend/.env.example)")
