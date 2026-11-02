"""Registro de extractores disponibles.

Uso desde la terminal (carpeta backend):
    python -m app.extractores                 lista los extractores
    python -m app.extractores <nombre>        ejecuta uno
    python -m app.extractores --todos         ejecuta todos

El nombre coincide con operativo.fuente_datos.extractor, que también define la
frecuencia de la ejecución automática.
"""
from .base import Dato, Extractor
from .catastro_turistico import CatastroTuristico
from .hosteleria_cuenca import HosteleriaCuenca
from .inec_poblacion import InecPoblacion
from .sri_ventas import SriVentas

# nombre corto -> clase. Cada fuente nueva se agrega aquí.
EXTRACTORES: dict[str, type[Extractor]] = {
    "sri_ventas": SriVentas,
    "catastro_turistico": CatastroTuristico,
    "hosteleria_cuenca": HosteleriaCuenca,
    "inec_poblacion": InecPoblacion,
}

__all__ = ["Dato", "Extractor", "EXTRACTORES"]
