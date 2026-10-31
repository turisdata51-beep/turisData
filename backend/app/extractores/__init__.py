"""Registro de extractores disponibles.

Uso desde la terminal (carpeta backend):
    python -m app.extractores                 lista los extractores
    python -m app.extractores <nombre>        ejecuta uno
    python -m app.extractores --todos         ejecuta todos
"""
from .base import Dato, Extractor
from .sri_ventas import SriVentas

# nombre corto -> clase. Cada fuente nueva se agrega aquí.
EXTRACTORES: dict[str, type[Extractor]] = {
    "sri_ventas": SriVentas,
}

__all__ = ["Dato", "Extractor", "EXTRACTORES"]
