"""API del panel de administración. Cada ruta declara qué roles pueden usarla."""
import csv
import io
import json
from datetime import date

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from .calculo import recalcular
from .config import PLANTILLA_XLSX
from .db import fila, filas, transaccion
from .importador import importar
from .seguridad import auditar, hash_contrasena, requiere, usuario_actual

router = APIRouter(prefix="/api/admin", tags=["admin"])

TODOS = ("administrador", "analista", "consulta", "asociado")
GESTION = ("administrador", "analista")
INTERNOS = ("administrador", "analista", "consulta")
TAMANO_MAXIMO = 5 * 1024 * 1024


# ----------------------------------------------------------------------------- resumen
@router.get("/resumen")
def resumen(u=Depends(requiere(*INTERNOS))):
    """Indicadores internos de calidad Q1–Q5 y conteos generales."""
    q1 = fila("""SELECT o.periodo_inicio AS periodo, o.valor FROM analitico.observacion o
                 JOIN operativo.geografia g ON g.id = o.geografia_id
                 WHERE o.indicador_codigo = 'Q1' AND g.nivel = 'canton'
                 ORDER BY o.periodo_inicio DESC LIMIT 1""")
    ultima = fila("""SELECT id, recibido_en, registros_recibidos, registros_validos,
                            campos_criticos_esperados, campos_criticos_validos
                     FROM operativo.carga_datos WHERE estado <> 'recibida' ORDER BY id DESC LIMIT 1""")
    fuentes = filas("""
        SELECT f.codigo, f.nombre, f.sla_dias, f.prioritaria,
               max(c.recibido_en) AS ultima_carga,
               extract(epoch FROM now() - max(c.recibido_en)) / 86400 AS dias
        FROM operativo.fuente_datos f
        LEFT JOIN operativo.carga_datos c ON c.fuente_id = f.id AND c.estado IN ('publicada', 'con_errores')
        WHERE f.activa AND f.tipo_fuente <> 'sistema'
        GROUP BY f.id ORDER BY f.prioritaria DESC, f.nombre""")
    prioritarias = [f for f in fuentes if f["prioritaria"]]
    al_dia = [f for f in prioritarias if f["dias"] is not None and f["sla_dias"] and f["dias"] <= f["sla_dias"]]

    def pct(a, b):
        return round(a / b * 100, 1) if b else None

    return {
        "q1_cobertura": {"periodo": q1["periodo"], "valor": float(q1["valor"])} if q1 and q1["valor"] is not None else None,
        "q2_completitud": pct(ultima["campos_criticos_validos"], ultima["campos_criticos_esperados"]) if ultima else None,
        "q3_frescura": [{**f, "dias": round(float(f["dias"]), 1) if f["dias"] is not None else None} for f in fuentes],
        "q4_fuentes_al_dia": pct(len(al_dia), len(prioritarias)),
        "q5_registros_validos": pct(ultima["registros_validos"], ultima["registros_recibidos"]) if ultima else None,
        "ultima_carga": ultima,
        "conteos": fila("""SELECT
            (SELECT count(*) FROM operativo.establecimiento WHERE participa_hasta IS NULL) AS establecimientos,
            (SELECT count(*) FROM operativo.usuario WHERE activo) AS usuarios,
            (SELECT count(*) FROM operativo.carga_datos) AS cargas,
            (SELECT count(*) FROM operativo.reporte_alojamiento_mensual WHERE vigente) AS reportes"""),
        "metas": {r["clave"]: r["valor"] for r in filas("SELECT clave, valor FROM operativo.parametro")},
    }


# ----------------------------------------------------------------------------- cargas
@router.get("/plantilla")
def plantilla(u=Depends(requiere(*TODOS))):
    return FileResponse(PLANTILLA_XLSX, filename=PLANTILLA_XLSX.name)


@router.post("/cargas")
async def subir(archivo: UploadFile = File(...), u=Depends(requiere("administrador", "analista", "asociado"))):
    contenido = await archivo.read()
    if len(contenido) > TAMANO_MAXIMO:
        raise HTTPException(413, "El archivo supera los 5 MB")
    resultado = importar(contenido, archivo.filename or "archivo", u)
    auditar(u["id"], "carga", "carga_datos", resultado["id"],
            "ok" if resultado["estado"] != "rechazada" else "error",
            {"archivo": archivo.filename, "estado": resultado["estado"], "validos": resultado["registros_validos"]})
    return resultado


@router.get("/cargas")
def cargas(u=Depends(requiere(*TODOS))):
    return filas("""
        SELECT c.id, c.nombre_archivo, c.recibido_en, c.estado, c.registros_recibidos, c.registros_validos,
               c.registros_rechazados, f.nombre AS fuente, us.nombre AS usuario,
               (SELECT count(*) FROM operativo.carga_error e WHERE e.carga_id = c.id AND e.severidad = 'error') AS errores,
               (SELECT count(*) FROM operativo.carga_error e WHERE e.carga_id = c.id AND e.severidad = 'advertencia') AS advertencias
        FROM operativo.carga_datos c
        JOIN operativo.fuente_datos f ON f.id = c.fuente_id
        LEFT JOIN operativo.usuario us ON us.id = c.usuario_id
        WHERE (:asociado = false OR c.usuario_id = :uid)
        ORDER BY c.id DESC LIMIT 200""", asociado=u["rol"] == "asociado", uid=u["id"])


@router.get("/cargas/{carga_id}/errores")
def errores(carga_id: int, u=Depends(requiere(*TODOS))):
    carga = fila("SELECT usuario_id FROM operativo.carga_datos WHERE id = :c", c=carga_id)
    if not carga or (u["rol"] == "asociado" and carga["usuario_id"] != u["id"]):
        raise HTTPException(404, "Carga no encontrada")
    return filas("""SELECT fila, campo, valor, regla, mensaje, severidad FROM operativo.carga_error
                    WHERE carga_id = :c ORDER BY fila NULLS FIRST, id""", c=carga_id)


@router.get("/mis-reportes")
def mis_reportes(u=Depends(requiere("asociado"))):
    return filas("""SELECT periodo, habitaciones_noche_disponibles, habitaciones_noche_ocupadas,
                           llegadas_residentes + llegadas_no_residentes AS llegadas,
                           noches_residentes + noches_no_residentes AS noches, ingreso_habitaciones_usd, carga_id
                    FROM operativo.reporte_alojamiento_mensual
                    WHERE establecimiento_id = :e AND vigente ORDER BY periodo DESC""", e=u["establecimiento_id"])


@router.post("/recalcular")
def forzar_recalculo(u=Depends(requiere(*GESTION))):
    n = recalcular()
    auditar(u["id"], "recalculo", detalle={"observaciones": n})
    return {"observaciones": n}


# ----------------------------------------------------------------------------- establecimientos
class Establecimiento(BaseModel):
    codigo_camara: str = Field(min_length=2, max_length=30)
    nombre_comercial: str = Field(min_length=2)
    tipo_alojamiento: str
    categoria: str
    parroquia: str
    participa_desde: date
    participa_hasta: date | None = None


@router.get("/parroquias")
def lista_parroquias(u=Depends(usuario_actual)):
    return filas("SELECT id, nombre, tipo FROM operativo.geografia WHERE nivel = 'parroquia' ORDER BY tipo DESC, nombre")


@router.get("/establecimientos")
def establecimientos(u=Depends(requiere(*GESTION))):
    return filas("""
        SELECT e.id, e.codigo_camara, e.nombre_comercial, e.tipo_alojamiento, e.categoria, g.nombre AS parroquia,
               e.participa_desde, e.participa_hasta,
               (SELECT max(periodo) FROM operativo.reporte_alojamiento_mensual r
                WHERE r.establecimiento_id = e.id AND r.vigente) AS ultimo_reporte
        FROM operativo.establecimiento e JOIN operativo.geografia g ON g.id = e.parroquia_id
        ORDER BY e.codigo_camara""")


def _guardar_establecimiento(datos: Establecimiento, establecimiento_id: int | None):
    parroquia = fila("SELECT id FROM operativo.geografia WHERE nivel = 'parroquia' AND nombre = :n", n=datos.parroquia)
    if not parroquia:
        raise HTTPException(400, "Parroquia no válida")
    valores = {**datos.model_dump(), "parroquia_id": parroquia["id"], "id": establecimiento_id}
    try:
        with transaccion() as con:
            if establecimiento_id is None:
                return con.execute(text("""
                    INSERT INTO operativo.establecimiento
                      (codigo_camara, nombre_comercial, tipo_alojamiento, categoria, parroquia_id, participa_desde, participa_hasta)
                    VALUES (:codigo_camara, :nombre_comercial, :tipo_alojamiento, :categoria, :parroquia_id,
                            :participa_desde, :participa_hasta) RETURNING id"""), valores).scalar()
            con.execute(text("""
                UPDATE operativo.establecimiento SET codigo_camara = :codigo_camara, nombre_comercial = :nombre_comercial,
                  tipo_alojamiento = :tipo_alojamiento, categoria = :categoria, parroquia_id = :parroquia_id,
                  participa_desde = :participa_desde, participa_hasta = :participa_hasta
                WHERE id = :id"""), valores)
            return establecimiento_id
    except IntegrityError:
        raise HTTPException(409, "Ya existe un establecimiento con ese código, o las fechas no son coherentes")


@router.post("/establecimientos")
def crear_establecimiento(datos: Establecimiento, u=Depends(requiere(*GESTION))):
    nuevo = _guardar_establecimiento(datos, None)
    auditar(u["id"], "crear", "establecimiento", nuevo, detalle=datos.model_dump())
    return {"id": nuevo}


@router.put("/establecimientos/{establecimiento_id}")
def editar_establecimiento(establecimiento_id: int, datos: Establecimiento, u=Depends(requiere(*GESTION))):
    _guardar_establecimiento(datos, establecimiento_id)
    auditar(u["id"], "editar", "establecimiento", establecimiento_id, detalle=datos.model_dump())
    recalcular()  # cambiar fechas de participación afecta la cobertura (Q1)
    return {"id": establecimiento_id}


# ----------------------------------------------------------------------------- usuarios
class UsuarioNuevo(BaseModel):
    correo: EmailStr
    nombre: str = Field(min_length=2)
    rol: str
    contrasena: str = Field(min_length=10)
    codigo_establecimiento: str | None = None


class UsuarioCambio(BaseModel):
    nombre: str | None = None
    rol: str | None = None
    activo: bool | None = None
    contrasena: str | None = Field(default=None, min_length=10)


@router.get("/usuarios")
def usuarios(u=Depends(requiere("administrador"))):
    return filas("""SELECT u.id, u.correo, u.nombre, u.rol, u.activo, u.creado_en, u.ultimo_acceso,
                           e.codigo_camara AS establecimiento
                    FROM operativo.usuario u LEFT JOIN operativo.establecimiento e ON e.id = u.establecimiento_id
                    ORDER BY u.id""")


@router.post("/usuarios")
def crear_usuario(datos: UsuarioNuevo, u=Depends(requiere("administrador"))):
    establecimiento_id = None
    if datos.rol == "asociado":
        est = fila("SELECT id FROM operativo.establecimiento WHERE codigo_camara = :c", c=datos.codigo_establecimiento)
        if not est:
            raise HTTPException(400, "Un asociado necesita un código de establecimiento válido")
        establecimiento_id = est["id"]
    try:
        with transaccion() as con:
            nuevo = con.execute(text("""
                INSERT INTO operativo.usuario (correo, nombre, hash_contrasena, rol, establecimiento_id)
                VALUES (:c, :n, :h, :r, :e) RETURNING id"""),
                dict(c=datos.correo.lower(), n=datos.nombre, h=hash_contrasena(datos.contrasena),
                     r=datos.rol, e=establecimiento_id)).scalar()
    except IntegrityError:
        raise HTTPException(409, "El correo ya existe o el rol no es válido")
    auditar(u["id"], "crear", "usuario", nuevo, detalle={"correo": datos.correo, "rol": datos.rol})
    return {"id": nuevo}


@router.patch("/usuarios/{usuario_id}")
def editar_usuario(usuario_id: int, datos: UsuarioCambio, u=Depends(requiere("administrador"))):
    if usuario_id == u["id"] and (datos.activo is False or (datos.rol and datos.rol != "administrador")):
        raise HTTPException(400, "No puede desactivarse ni quitarse el rol de administrador a sí mismo")
    cambios = {k: v for k, v in datos.model_dump().items() if v is not None}
    if "contrasena" in cambios:
        cambios["hash_contrasena"] = hash_contrasena(cambios.pop("contrasena"))
    if not cambios:
        return {"id": usuario_id}
    try:
        with transaccion() as con:
            con.execute(text(f"""UPDATE operativo.usuario SET {', '.join(f'{k} = :{k}' for k in cambios)}
                                 WHERE id = :id"""), {**cambios, "id": usuario_id})
    except IntegrityError:
        raise HTTPException(400, "Cambio no válido (un asociado debe tener establecimiento)")
    auditar(u["id"], "editar", "usuario", usuario_id,
            detalle={k: v for k, v in cambios.items() if k != "hash_contrasena"})
    return {"id": usuario_id}


# ----------------------------------------------------------------------------- fuentes, indicadores, contenido
@router.get("/fuentes")
def fuentes(u=Depends(requiere(*INTERNOS))):
    return filas("SELECT * FROM operativo.fuente_datos ORDER BY prioritaria DESC, nombre")


@router.get("/indicadores")
def indicadores(u=Depends(requiere(*INTERNOS))):
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


# ----------------------------------------------------------------------------- exportación (RF-08)
@router.get("/exportar")
def exportar(u=Depends(requiere(*INTERNOS))):
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
    return StreamingResponse(iter(["﻿" + salida.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=observatorio_indicadores.csv"})
