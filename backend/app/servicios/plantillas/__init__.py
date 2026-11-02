"""Plantillas de carga disponibles en el panel. Cada una se registra aquí con su código."""
from .alojamiento import Alojamiento
from .base import Plantilla
from .complementarias import Accesibilidad, Consumos, Empleo
from .series_externas import SeriesExternas

PLANTILLAS: dict[str, Plantilla] = {p.codigo: p for p in (
    Alojamiento(), Empleo(), Accesibilidad(), Consumos(), SeriesExternas())}


def importar(contenido: bytes, nombre: str, usuario: dict, plantilla: str = "alojamiento") -> dict:
    return PLANTILLAS[plantilla].importar(contenido, nombre, usuario)
