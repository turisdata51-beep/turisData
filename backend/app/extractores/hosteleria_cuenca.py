"""Hostelería del cantón Cuenca (portal municipal Cuenca en Datos).

Lee la página del conjunto, descarga la base municipal de alojamientos más reciente y guarda totales de
establecimientos, habitaciones y plazas instaladas, en total y por tipo. La base
no trae parroquia, así que todo queda a nivel cantonal. Los datos personales
(responsable, teléfono, correo) no se guardan.
"""
import csv
import io
import json
from calendar import monthrange
from collections import defaultdict
from datetime import date

from .base import Dato, Extractor
from . import ckan

PORTAL = "https://cuencaendatos.cuenca.gob.ec"
PAQUETE = "hosteleria"


def _entero(valor: str) -> int | None:
    try:
        return int(float(str(valor).strip().replace(",", ".")))
    except ValueError:
        return None


class HosteleriaCuenca(Extractor):
    fuente_codigo = "hosteleria_cuenca"
    url = f"{PORTAL}/dataset/{PAQUETE}"

    def descargar(self) -> bytes:
        # Los archivos _DD_ y _PM_ son diccionario de datos y metadatos, no la base
        recurso = ckan.mas_reciente(self, self.url, ".csv")
        crudo = ckan.descargar(self, recurso)
        try:
            texto = crudo.decode("utf-8-sig")
        except UnicodeDecodeError:
            texto = crudo.decode("latin-1")
        primera = texto.split("\n", 1)[0]
        lector = csv.DictReader(io.StringIO(texto), delimiter=";" if primera.count(";") > primera.count(",") else ",")
        totales = defaultdict(lambda: {"establecimientos": 0, "habitaciones": 0, "plazas": 0})
        for fila in lector:
            tipo = (fila.get("tipo") or "SIN TIPO").strip().upper()
            for grupo in ("TOTAL", tipo):
                totales[grupo]["establecimientos"] += 1
                totales[grupo]["habitaciones"] += _entero(fila.get("nro_habitaciones", "")) or 0
                totales[grupo]["plazas"] += _entero(fila.get("nro_plazas", "")) or 0
        if not totales:
            raise ValueError("La base de hostelería está vacía; revise si cambió el formato")
        resumen = {"corte": recurso.corte.isoformat(), "archivo": recurso.nombre, "totales": dict(sorted(totales.items()))}
        return json.dumps(resumen, ensure_ascii=False).encode("utf-8")

    def interpretar(self, contenido: bytes) -> list[Dato]:
        resumen = json.loads(contenido)
        corte = date.fromisoformat(resumen["corte"])
        fin = date(corte.year, corte.month, monthrange(corte.year, corte.month)[1])
        datos = []
        for grupo, valores in resumen["totales"].items():
            dimensiones = {} if grupo == "TOTAL" else {"tipo": grupo}
            for medida, valor in valores.items():
                datos.append(Dato(f"hosteleria_{medida}", corte, fin, valor, dimensiones=dimensiones))
        return datos
