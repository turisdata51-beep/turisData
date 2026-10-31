"""Sincroniza docs/diccionario_indicadores.yaml con analitico.indicador (RF-06, RF-12)."""
import json
from datetime import date

import yaml
from sqlalchemy import text

from .config import DICCIONARIO
from .db import transaccion


def cargar() -> dict:
    return yaml.safe_load(DICCIONARIO.read_text(encoding="utf-8"))


def sincronizar() -> int:
    """Registra versiones nuevas; nunca modifica una versión ya registrada."""
    nuevas = 0
    with transaccion() as con:
        for ficha in cargar()["indicadores"]:
            existe = con.execute(text(
                "SELECT 1 FROM analitico.indicador WHERE codigo = :c AND version = :v"),
                dict(c=ficha["codigo"], v=ficha["version"])).first()
            if existe:
                continue
            con.execute(text(
                """UPDATE analitico.indicador SET vigente_hasta = :hoy
                   WHERE codigo = :c AND vigente_hasta IS NULL"""), dict(c=ficha["codigo"], hoy=date.today()))
            con.execute(text(
                """INSERT INTO analitico.indicador
                     (codigo, version, nombre, tipo_base, unidad, universo, ficha, vigente_desde)
                   VALUES (:c, :v, :n, :t, :u, :un, CAST(:f AS jsonb), :hoy)"""),
                dict(c=ficha["codigo"], v=ficha["version"], n=ficha["nombre"], t=ficha["tipo_base"],
                     u=ficha["unidad"], un=ficha["universo"], f=json.dumps(ficha, ensure_ascii=False),
                     hoy=date.today()))
            nuevas += 1
    return nuevas
