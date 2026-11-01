"""Indicadores, contenido del sitio, auditoría y exportación (RF-08, RF-10)."""
import csv
import io
import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import text

from ...nucleo.db import fila, filas, transaccion
from ...nucleo.seguridad import ROLES_INTERNOS, auditar, requiere

router = APIRouter()


@router.get("/indicadores")
def indicadores(u=Depends(requiere(*ROLES_INTERNOS))):
    return filas("""SELECT codigo, version, nombre, tipo_base, unidad, universo, vigente_desde, vigente_hasta,
                           ficha->>'fase' AS fase, ficha->>'formula_texto' AS formula,
                           (SELECT count(*) FROM analitico.observacion o
                            WHERE o.indicador_codigo = i.codigo AND o.indicador_version = i.version) AS observaciones
                    FROM analitico.indicador i ORDER BY codigo, version""")


@router.get("/contenido")
def ver_contenido(u=Depends(requiere("administrador"))):
    return fila("SELECT valor FROM operativo.contenido_sitio WHERE clave = 'landing'")["valor"]


@router.put("/contenido")
def guardar_contenido(valor: dict, u=Depends(requiere("administrador"))):
    with transaccion() as con:
        con.execute(text("""UPDATE operativo.contenido_sitio SET valor = CAST(:v AS jsonb), actualizado_en = now(),
                            actualizado_por = :u WHERE clave = 'landing'"""),
                    dict(v=json.dumps(valor, ensure_ascii=False), u=u["id"]))
    auditar(u["id"], "cambio_config", "contenido_sitio", "landing")
    return valor


@router.get("/auditoria")
def auditoria(u=Depends(requiere("administrador"))):
    return filas("""SELECT a.id, a.ocurrido_en, us.correo AS usuario, a.accion, a.entidad, a.entidad_id,
                           a.resultado, a.detalle
                    FROM operativo.auditoria a LEFT JOIN operativo.usuario us ON us.id = a.usuario_id
                    ORDER BY a.id DESC LIMIT 300""")


@router.get("/exportar")
def exportar(u=Depends(requiere(*ROLES_INTERNOS))):
    datos = filas("""
        SELECT o.indicador_codigo, i.nombre, o.indicador_version, o.periodo_inicio, g.nivel, g.nombre AS geografia,
               o.dimensiones::text AS dimensiones, o.valor, i.unidad, o.bandera, o.n_unidades, o.cobertura_pct
        FROM analitico.observacion o
        JOIN analitico.indicador i ON i.codigo = o.indicador_codigo AND i.version = o.indicador_version
        JOIN operativo.geografia g ON g.id = o.geografia_id
        WHERE o.publicable ORDER BY o.indicador_codigo, o.periodo_inicio, g.nivel, g.nombre""")
    salida = io.StringIO()
    if datos:
        escritor = csv.DictWriter(salida, fieldnames=list(datos[0].keys()))
        escritor.writeheader()
        escritor.writerows(datos)
    auditar(u["id"], "exportacion", detalle={"filas": len(datos)})
    # BOM para que Excel reconozca UTF-8
    return StreamingResponse(iter(["﻿" + salida.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=observatorio_indicadores.csv"})
