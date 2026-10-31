"""Marco común para los extractores (web scraping, descargas y APIs).

Cada fuente se implementa como una subclase de Extractor con dos métodos:
  descargar() -> bytes          trae el contenido crudo (HTML, XLSX, PDF, JSON)
  interpretar(contenido) -> [Dato]  lo convierte en observaciones normalizadas

El método ejecutar() se encarga del resto: respeta robots.txt, evita repetir el
trabajo si la fuente no cambió, guarda el histórico sin borrar versiones
anteriores y deja registro de cada ejecución en operativo.ejecucion_extractor.
"""
import hashlib
import json
import time
from dataclasses import dataclass, field
from datetime import date
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx
from sqlalchemy import text

from ..db import transaccion

AGENTE = "TurisData-Observatorio/0.1 (proyecto de titulacion; Camara de Turismo del Azuay)"
PAUSA_ENTRE_PETICIONES = 2.0  # segundos, para no sobrecargar los sitios


@dataclass
class Dato:
    variable: str
    periodo_inicio: date
    periodo_fin: date
    valor: float
    periodicidad: str = "mensual"
    geografia: str = "Cuenca"          # nombre en operativo.geografia
    evento: str | None = None          # ej. "Carnaval 2026" para periodicidad feriado
    dimensiones: dict = field(default_factory=dict)


class FuenteNoPermitida(Exception):
    """robots.txt del sitio no permite acceder a esa ruta."""


class Extractor:
    fuente_codigo: str = ""   # operativo.fuente_datos.codigo
    url: str = ""

    def __init__(self):
        self._cliente = httpx.Client(headers={"User-Agent": AGENTE}, timeout=60, follow_redirects=True)
        self._ultima_peticion = 0.0
        self._robots: dict[str, RobotFileParser] = {}

    # --- a implementar por cada fuente -------------------------------------------------
    def descargar(self) -> bytes:
        return self.obtener(self.url).content

    def interpretar(self, contenido: bytes) -> list[Dato]:
        raise NotImplementedError

    # --- utilidades HTTP con cortesía -------------------------------------------------
    def permitido(self, url: str) -> bool:
        partes = urlparse(url)
        base = f"{partes.scheme}://{partes.netloc}"
        if base not in self._robots:
            robots = RobotFileParser()
            try:
                r = self._cliente.get(f"{base}/robots.txt")
                robots.parse(r.text.splitlines() if r.status_code == 200 else [])
            except httpx.HTTPError:
                robots.parse([])
            self._robots[base] = robots
        return self._robots[base].can_fetch(AGENTE, url)

    def obtener(self, url: str, **kwargs) -> httpx.Response:
        if not self.permitido(url):
            raise FuenteNoPermitida(f"robots.txt no permite acceder a {url}")
        espera = PAUSA_ENTRE_PETICIONES - (time.monotonic() - self._ultima_peticion)
        if espera > 0:
            time.sleep(espera)
        respuesta = self._cliente.get(url, **kwargs)
        self._ultima_peticion = time.monotonic()
        respuesta.raise_for_status()
        return respuesta

    # --- ejecución con trazabilidad ------------------------------------------------------
    def ejecutar(self, usuario_id: int | None = None, forzar: bool = False) -> dict:
        with transaccion() as con:
            fuente_id = con.execute(text("SELECT id FROM operativo.fuente_datos WHERE codigo = :c"),
                                    dict(c=self.fuente_codigo)).scalar()
            if fuente_id is None:
                raise ValueError(f"La fuente {self.fuente_codigo} no está registrada en operativo.fuente_datos")
            ejecucion_id = con.execute(text(
                """INSERT INTO operativo.ejecucion_extractor (fuente_id, extractor, url_origen, usuario_id)
                   VALUES (:f, :e, :u, :usr) RETURNING id"""),
                dict(f=fuente_id, e=type(self).__name__, u=self.url, usr=usuario_id)).scalar()

        resultado = dict(id=ejecucion_id, estado="error", nuevos=0, actualizados=0, mensaje=None)
        try:
            contenido = self.descargar()
            huella = hashlib.sha256(contenido).hexdigest()
            with transaccion() as con:
                anterior = con.execute(text(
                    """SELECT hash_contenido FROM operativo.ejecucion_extractor
                       WHERE fuente_id = :f AND estado IN ('ok', 'sin_cambios') AND id <> :id
                       ORDER BY id DESC LIMIT 1"""), dict(f=fuente_id, id=ejecucion_id)).scalar()
            if anterior == huella and not forzar:
                resultado.update(estado="sin_cambios", mensaje="La fuente no cambió desde la última ejecución")
            else:
                datos = self.interpretar(contenido)
                nuevos, actualizados = self._guardar(datos, ejecucion_id)
                resultado.update(estado="ok", nuevos=nuevos, actualizados=actualizados,
                                 mensaje=f"{len(datos)} datos leídos")
            resultado["hash"] = huella
        except Exception as e:  # se registra cualquier falla para verla en el panel
            resultado["mensaje"] = f"{type(e).__name__}: {e}"[:1000]
        finally:
            self._cliente.close()

        with transaccion() as con:
            con.execute(text(
                """UPDATE operativo.ejecucion_extractor
                   SET terminada_en = now(), estado = :estado, hash_contenido = :hash,
                       registros_nuevos = :nuevos, registros_actualizados = :actualizados, mensaje = :mensaje
                   WHERE id = :id"""),
                dict(estado=resultado["estado"], hash=resultado.get("hash"), nuevos=resultado["nuevos"],
                     actualizados=resultado["actualizados"], mensaje=resultado["mensaje"], id=ejecucion_id))
        return resultado

    def _guardar(self, datos: list[Dato], ejecucion_id: int) -> tuple[int, int]:
        """Inserta datos nuevos; si un valor cambió, marca el anterior como no vigente."""
        nuevos = actualizados = 0
        with transaccion() as con:
            geografias = dict(con.execute(text("SELECT nombre, id FROM operativo.geografia")).all())
            for d in datos:
                clave = dict(v=d.variable, g=geografias[d.geografia], ini=d.periodo_inicio, per=d.periodicidad,
                             ev=d.evento or "", dims=json.dumps(d.dimensiones, ensure_ascii=False, sort_keys=True))
                actual = con.execute(text(
                    """SELECT id, valor FROM operativo.observacion_externa
                       WHERE variable = :v AND geografia_id = :g AND periodo_inicio = :ini AND periodicidad = :per
                         AND coalesce(evento, '') = :ev AND dimensiones = CAST(:dims AS jsonb) AND vigente"""),
                    clave).first()
                if actual and float(actual.valor) == float(d.valor):
                    continue
                if actual:
                    con.execute(text("UPDATE operativo.observacion_externa SET vigente = false WHERE id = :id"),
                                dict(id=actual.id))
                    actualizados += 1
                else:
                    nuevos += 1
                con.execute(text(
                    """INSERT INTO operativo.observacion_externa
                         (variable, geografia_id, periodo_inicio, periodo_fin, periodicidad, evento, dimensiones,
                          valor, ejecucion_id)
                       VALUES (:v, :g, :ini, :fin, :per, NULLIF(:ev, ''), CAST(:dims AS jsonb), :valor, :ej)"""),
                    {**clave, "fin": d.periodo_fin, "valor": d.valor, "ej": ejecucion_id})
        return nuevos, actualizados
