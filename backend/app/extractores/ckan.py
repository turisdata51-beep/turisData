"""Scraping de portales de datos abiertos CKAN (datosabiertos.gob.ec, cuencaendatos.cuenca.gob.ec).

El robots.txt de estos portales prohíbe la API (/api/) a los robots, pero permite
las páginas de cada conjunto (/dataset/...) y la descarga de sus archivos. Por eso
se lee la página HTML del conjunto, se listan sus archivos y se elige el de fecha de
corte más reciente. Esa fecha solo aparece en el nombre del archivo.
"""
import re
import unicodedata
from dataclasses import dataclass
from datetime import date
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import Extractor

MESES = {"enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6, "julio": 7,
         "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12}
RECURSO = re.compile(r"/dataset/[^/]+/resource/([0-9a-f-]{36})$")


@dataclass
class Recurso:
    nombre: str
    pagina: str
    corte: date | None


def fecha_en_nombre(nombre: str) -> date | None:
    """'1era quincena Febrero Catastro Nacional 2025' o 'Hosteleria_2025Abril' -> date(2025, 2|4, 1)."""
    texto = unicodedata.normalize("NFKD", nombre).encode("ascii", "ignore").decode().lower()
    anio = re.search(r"(20\d{2})", texto)
    mes = next((n for m, n in MESES.items() if m in texto), None)
    if not anio or not mes:
        return None
    return date(int(anio.group(1)), mes, 1)


def recursos(extractor: Extractor, pagina_conjunto: str) -> list[Recurso]:
    """Archivos que lista la página HTML de un conjunto de datos."""
    html = BeautifulSoup(extractor.obtener(pagina_conjunto).text, "lxml")
    vistos, lista = set(), []
    for a in html.find_all("a", href=True):
        m = RECURSO.search(a["href"])
        if not m or m.group(1) in vistos:
            continue
        vistos.add(m.group(1))
        nombre = (a.get("title") or a.get_text(" ", strip=True)).strip()
        lista.append(Recurso(nombre, urljoin(pagina_conjunto, a["href"]), fecha_en_nombre(nombre)))
    return lista


def mas_reciente(extractor: Extractor, pagina_conjunto: str, extension: str, excluir: str | None = None) -> Recurso:
    """El archivo con la extensión pedida y la fecha de corte más reciente."""
    candidatos = [r for r in recursos(extractor, pagina_conjunto)
                  if r.corte and r.nombre.lower().endswith(extension)
                  and not (excluir and excluir.lower() in r.nombre.lower())]
    if not candidatos:
        raise ValueError(f"La página {pagina_conjunto} no lista archivos {extension} con fecha de corte")
    return max(candidatos, key=lambda r: r.corte)


def descargar(extractor: Extractor, recurso: Recurso) -> bytes:
    """Abre la página del archivo y sigue su enlace de descarga."""
    html = BeautifulSoup(extractor.obtener(recurso.pagina).text, "lxml")
    enlace = next((a["href"] for a in html.find_all("a", href=True) if "/download/" in a["href"]), None)
    if not enlace:
        raise ValueError(f"La página {recurso.pagina} no tiene enlace de descarga")
    return extractor.obtener(urljoin(recurso.pagina, enlace)).content
