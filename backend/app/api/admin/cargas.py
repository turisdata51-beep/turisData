"""Plantillas y carga de archivos (RF-03, RF-09), y consulta de los reportes propios del asociado."""
from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile

from ...nucleo.db import fila, filas
from ...nucleo.seguridad import ROLES_TODOS, auditar, requiere
from ...servicios.plantillas import PLANTILLAS, importar

router = APIRouter()

TAMANO_MAXIMO = 5 * 1024 * 1024
TIPOS_ARCHIVO = {"xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "csv": "text/csv"}


def _plantilla_permitida(codigo: str, usuario: dict):
    plantilla = PLANTILLAS.get(codigo)
    if not plantilla:
        raise HTTPException(404, "Plantilla no encontrada")
    if usuario["rol"] not in plantilla.roles:
        raise HTTPException(403, "Su rol no puede usar esta plantilla")
    return plantilla


@router.get("/plantillas")
def plantillas(u=Depends(requiere(*ROLES_TODOS))):
    """Plantillas que el usuario puede descargar y subir, con su lista de columnas."""
    return [dict(codigo=p.codigo, nombre=p.nombre, descripcion=p.descripcion, unidad=p.unidad, version=p.version,
                 columnas=[dict(nombre=c.nombre, tipo=c.tipo, obligatoria=c.obligatoria, descripcion=c.descripcion)
                           for c in p.columnas])
            for p in PLANTILLAS.values() if u["rol"] in p.roles]


@router.get("/plantillas/{codigo}.{extension}")
def descargar_plantilla(codigo: str, extension: str, u=Depends(requiere(*ROLES_TODOS))):
    if extension not in TIPOS_ARCHIVO:
        raise HTTPException(404, "Use .xlsx o .csv")
    plantilla = _plantilla_permitida(codigo, u)
    contenido = plantilla.generar_xlsx() if extension == "xlsx" else plantilla.generar_csv()
    return Response(contenido, media_type=TIPOS_ARCHIVO[extension],
                    headers={"Content-Disposition": f'attachment; filename="{plantilla.nombre_archivo(extension)}"'})


@router.post("/cargas")
async def subir(archivo: UploadFile = File(...), plantilla: str = Form("alojamiento"),
                u=Depends(requiere("administrador", "analista", "asociado"))):
    _plantilla_permitida(plantilla, u)
    contenido = await archivo.read()
    if len(contenido) > TAMANO_MAXIMO:
        raise HTTPException(413, "El archivo supera los 5 MB")
    resultado = importar(contenido, archivo.filename or "archivo", u, plantilla)
    auditar(u["id"], "carga", "carga_datos", resultado["id"],
            "ok" if resultado["estado"] != "rechazada" else "error",
            {"archivo": archivo.filename, "plantilla": plantilla, "estado": resultado["estado"],
             "validos": resultado["registros_validos"]})
    return resultado


@router.get("/cargas")
def cargas(u=Depends(requiere(*ROLES_TODOS))):
    lista = filas("""
        SELECT c.id, c.nombre_archivo, c.recibido_en, c.estado, c.plantilla, c.registros_recibidos, c.registros_validos,
               c.registros_rechazados, f.nombre AS fuente, us.nombre AS usuario,
               (SELECT count(*) FROM operativo.carga_error e WHERE e.carga_id = c.id AND e.severidad = 'error') AS errores,
               (SELECT count(*) FROM operativo.carga_error e WHERE e.carga_id = c.id AND e.severidad = 'advertencia') AS advertencias
        FROM operativo.carga_datos c
        JOIN operativo.fuente_datos f ON f.id = c.fuente_id
        LEFT JOIN operativo.usuario us ON us.id = c.usuario_id
        WHERE (:asociado = false OR c.usuario_id = :uid)
        ORDER BY c.id DESC LIMIT 200""", asociado=u["rol"] == "asociado", uid=u["id"])
    for c in lista:
        c["plantilla_nombre"] = PLANTILLAS[c["plantilla"]].nombre if c["plantilla"] in PLANTILLAS else c["plantilla"]
    return lista


@router.get("/cargas/{carga_id}/errores")
def errores(carga_id: int, u=Depends(requiere(*ROLES_TODOS))):
    carga = fila("SELECT usuario_id FROM operativo.carga_datos WHERE id = :c", c=carga_id)
    if not carga or (u["rol"] == "asociado" and carga["usuario_id"] != u["id"]):
        raise HTTPException(404, "Carga no encontrada")
    return filas("""SELECT fila, campo, valor, regla, mensaje, severidad FROM operativo.carga_error
                    WHERE carga_id = :c ORDER BY fila NULLS FIRST, id""", c=carga_id)


@router.get("/mis-reportes")
def mis_reportes(u=Depends(requiere("asociado"))):
    return filas("""SELECT periodo, habitaciones_noche_disponibles, habitaciones_noche_ocupadas,
                           llegadas_residentes + llegadas_no_residentes AS llegadas,
                           noches_residentes + noches_no_residentes AS noches, ingreso_habitaciones_usd
                    FROM operativo.reporte_alojamiento_mensual
                    WHERE establecimiento_id = :e AND vigente ORDER BY periodo DESC""", e=u["establecimiento_id"])
