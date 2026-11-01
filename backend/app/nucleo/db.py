from contextlib import contextmanager

from sqlalchemy import create_engine, text

from .config import DATABASE_URL

engine = create_engine(DATABASE_URL, pool_pre_ping=True)


@contextmanager
def transaccion():
    with engine.begin() as con:
        yield con


def filas(sql: str, **params) -> list[dict]:
    with engine.connect() as con:
        return [dict(r._mapping) for r in con.execute(text(sql), params)]


def fila(sql: str, **params) -> dict | None:
    resultado = filas(sql, **params)
    return resultado[0] if resultado else None
