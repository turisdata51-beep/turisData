"""Catastro turístico nacional (Portal de Datos Abiertos del Ecuador).

Lee la página del conjunto, descarga la versión más reciente del catastro en XLSX, filtra el cantón Cuenca y
guarda solo conteos: establecimientos por parroquia y actividad, y alojamientos
por clasificación. El archivo trae datos personales (RUC, representante, correo),
que no se guardan.
"""
import io
import json
from calendar import monthrange
from collections import Counter
from datetime import date

from openpyxl import load_workbook

from .base import Dato, Extractor
from . import ckan

PORTAL = "https://www.datosabiertos.gob.ec"
PAQUETE = "catastro-turistico-total"
CANTON = ("AZUAY", "CUENCA")
COLUMNAS = {"provincia": "Provincia", "canton": "Cantón", "parroquia": "Parroquia",
            "actividad": "Actividad / Modalidad", "clasificacion": "Clasificación"}


class CatastroTuristico(Extractor):
    fuente_codigo = "catastro_turistico"
    url = f"{PORTAL}/dataset/{PAQUETE}"

    def descargar(self) -> bytes:
        recurso = ckan.mas_reciente(self, self.url, ".xlsx")
        hoja = load_workbook(io.BytesIO(ckan.descargar(self, recurso)), read_only=True).worksheets[0]
        filas = hoja.iter_rows(values_only=True)
        encabezado = [str(c).strip() if c else "" for c in next(filas)]
        i = {clave: encabezado.index(nombre) for clave, nombre in COLUMNAS.items()}
        conteo = Counter()
        for f in filas:
            if (str(f[i["provincia"]]).strip(), str(f[i["canton"]]).strip()) != CANTON:
                continue
            conteo[(str(f[i["parroquia"]] or "").strip(), str(f[i["actividad"]]).strip(),
                    str(f[i["clasificacion"]]).strip())] += 1
        if not conteo:
            raise ValueError("El catastro no trae registros de Cuenca; revise si cambió el formato")
        # Solo conteos agregados: la huella cambia únicamente si cambian las cifras
        resumen = {"corte": recurso.corte.isoformat(), "archivo": recurso.nombre,
                   "conteos": sorted([list(k) + [n] for k, n in conteo.items()])}
        return json.dumps(resumen, ensure_ascii=False).encode("utf-8")

    def interpretar(self, contenido: bytes) -> list[Dato]:
        resumen = json.loads(contenido)
        corte = date.fromisoformat(resumen["corte"])
        fin = date(corte.year, corte.month, monthrange(corte.year, corte.month)[1])
        por_parroquia, por_actividad, por_clasificacion = Counter(), Counter(), Counter()
        for parroquia, actividad, clasificacion, n in resumen["conteos"]:
            if parroquia:
                por_parroquia[(parroquia, actividad)] += n
            por_actividad[actividad] += n
            if actividad == "ALOJAMIENTO":
                por_clasificacion[clasificacion] += n

        def dato(geografia, valor, **dimensiones):
            return Dato("catastro_establecimientos", corte, fin, valor, geografia=geografia, dimensiones=dimensiones)

        return ([dato(p, n, actividad=a) for (p, a), n in por_parroquia.items()]
                + [dato("Cuenca", n, actividad=a) for a, n in por_actividad.items()]
                + [dato("Cuenca", n, actividad="ALOJAMIENTO", clasificacion=c) for c, n in por_clasificacion.items()])
