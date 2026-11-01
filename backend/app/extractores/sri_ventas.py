"""SRI, datos abiertos: ventas mensuales por cantón y sección CIIU.

Lee la página https://www.sri.gob.ec/datasets, encuentra los enlaces a
sri_ventas_AAAA.csv (cambian de identificador en cada publicación) y guarda las
ventas de la sección I (alojamiento y servicios de comidas) del cantón Cuenca.

Limitación: la sección I junta alojamiento (I55) y comidas (I56); el SRI no los
separa en datos abiertos.
"""
import csv
import io
import re
from calendar import monthrange
from datetime import date

from bs4 import BeautifulSoup

from ..nucleo.db import fila
from .base import Dato, Extractor

PRIMER_ANIO = 2018
SECCION = "I"
CANTON = ("AZUAY", "CUENCA")


class SriVentas(Extractor):
    fuente_codigo = "sri_ventas"
    url = "https://www.sri.gob.ec/datasets"

    def anios(self) -> list[int]:
        # La primera vez trae todo el histórico; después solo el año en curso y el anterior (pueden corregirse)
        hay_datos = fila(
            "SELECT 1 FROM operativo.observacion_externa WHERE variable = 'sri_ventas_seccion_i' LIMIT 1")
        actual = date.today().year
        return list(range(PRIMER_ANIO if not hay_datos else actual - 1, actual + 1))

    def descargar(self) -> bytes:
        pagina = BeautifulSoup(self.obtener(self.url).text, "lxml")
        enlaces = {}
        for a in pagina.find_all("a", href=True):
            m = re.search(r"sri_ventas_(\d{4})\.csv", a["href"].strip())
            if m:
                enlaces[int(m.group(1))] = a["href"].strip()
        filas = []
        for anio in self.anios():
            if anio not in enlaces:
                continue
            for mes, total in self._filas_cuenca(self.obtener(enlaces[anio]).content):
                filas.append(f"{anio}|{mes:02d}|{total}")
        if not filas:
            raise ValueError("No se encontraron filas de Cuenca; revise si cambió el formato de la página o del archivo")
        return "\n".join(["ANIO|MES|TOTAL_VENTAS", *sorted(filas)]).encode("utf-8")

    @staticmethod
    def _filas_cuenca(crudo: bytes):
        """Devuelve (mes, total_ventas) de Cuenca, sección I.

        El formato varía entre años: separador | o coma, codificación UTF-8 o Latin-1,
        y la columna se llama TOTAL_VENTA o TOTAL_VENTAS. Se ubica todo por nombre.
        """
        try:
            texto = crudo.decode("utf-8-sig")
        except UnicodeDecodeError:
            texto = crudo.decode("latin-1")
        primera = texto.split("\n", 1)[0]
        separador = "|" if primera.count("|") > primera.count(",") else ","
        lector = csv.reader(io.StringIO(texto), delimiter=separador)
        columnas = [c.strip().upper() for c in next(lector)]
        i_mes, i_sec, i_prov, i_can = (columnas.index(c) for c in ("MES", "CODIGO_SECTOR_N1", "PROVINCIA", "CANTON"))
        i_total = next(i for i, c in enumerate(columnas) if c.startswith("TOTAL_VENTA"))
        for p in lector:
            if len(p) > i_total and p[i_sec].strip() == SECCION and (p[i_prov].strip(), p[i_can].strip()) == CANTON:
                valor = p[i_total].strip()
                if "," in valor and "." not in valor:  # coma decimal
                    valor = valor.replace(",", ".")
                yield int(p[i_mes]), float(valor)

    def interpretar(self, contenido: bytes) -> list[Dato]:
        datos = []
        for r in csv.DictReader(io.StringIO(contenido.decode("utf-8")), delimiter="|"):
            anio, mes = int(r["ANIO"]), int(r["MES"])
            datos.append(Dato(
                variable="sri_ventas_seccion_i",
                periodo_inicio=date(anio, mes, 1),
                periodo_fin=date(anio, mes, monthrange(anio, mes)[1]),
                valor=float(r["TOTAL_VENTAS"]),
            ))
        return datos

