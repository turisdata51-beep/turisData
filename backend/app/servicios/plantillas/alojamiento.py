"""Reporte mensual de alojamiento: la plantilla principal de los establecimientos (A1–A5, B2–B7, D4)."""
from sqlalchemy import text

from .base import Columna, Contexto, Plantilla, dias_del_mes

TIPOS_ALOJAMIENTO = ("Hotel", "Hostal", "Hostería", "Hacienda turística", "Lodge", "Resort",
                     "Refugio", "Campamento turístico", "Casa de huéspedes")
CATEGORIAS = ("1 estrella", "2 estrellas", "3 estrellas", "4 estrellas", "5 estrellas", "Categoría única")


class Alojamiento(Plantilla):
    codigo = "alojamiento"
    nombre = "Reporte mensual de alojamiento"
    descripcion = "Capacidad, ocupación, huéspedes y noches de cada establecimiento en el mes."
    unidad = "establecimiento y mes"
    fuente_codigo = "plantilla_alojamiento_camara"
    tabla = "operativo.reporte_alojamiento_mensual"
    solo_referencia = ("tipo_alojamiento", "categoria", "parroquia")
    columnas = [
        Columna("periodo", "mes", "Mes reportado en formato AAAA-MM (ej. 2026-09)."),
        Columna("codigo_establecimiento", "establecimiento", "Código asignado por la Cámara (no usar RUC ni cédula)."),
        Columna("tipo_alojamiento", "lista", "Clasificación según el Reglamento de Alojamiento Turístico.", opciones=TIPOS_ALOJAMIENTO),
        Columna("categoria", "lista", "Categoría registrada en el catastro.", opciones=CATEGORIAS),
        Columna("parroquia", "lista", "Parroquia del cantón Cuenca donde está el establecimiento."),
        Columna("habitaciones_instaladas", "entero", "Habitaciones que tiene el establecimiento (capacidad física)."),
        Columna("plazas_instaladas", "entero", "Camas o plazas instaladas. Una cama doble = 2 plazas."),
        Columna("dias_operacion", "entero", "Días del mes en que el establecimiento estuvo abierto."),
        Columna("habitaciones_noche_disponibles", "entero", "Suma, día por día, de las habitaciones a la venta (sin las fuera de servicio)."),
        Columna("habitaciones_noche_ocupadas", "entero", "Suma, día por día, de las habitaciones vendidas."),
        Columna("plazas_cama_noche_disponibles", "entero", "Suma, día por día, de las plazas a la venta."),
        Columna("llegadas_residentes", "entero", "Huéspedes que hicieron check-in en el mes y viven en Ecuador."),
        Columna("llegadas_no_residentes", "entero", "Huéspedes que hicieron check-in en el mes y viven fuera de Ecuador."),
        Columna("noches_residentes", "entero", "Noches pasadas en el mes por huéspedes residentes (1 persona × 1 noche = 1)."),
        Columna("noches_no_residentes", "entero", "Noches pasadas en el mes por huéspedes no residentes."),
        Columna("ingreso_habitaciones_usd", "decimal", "OPCIONAL. Venta de habitaciones del mes en USD, sin IVA ni 10 % de servicio.", obligatoria=False),
        Columna("observaciones", "texto", "OPCIONAL. Cierres, remodelaciones, eventos u otras novedades.", obligatoria=False),
    ]
    reglas_texto = [
        "habitaciones_noche_ocupadas <= habitaciones_noche_disponibles",
        "habitaciones_noche_disponibles <= habitaciones_instaladas × días del mes",
        "plazas_cama_noche_disponibles <= plazas_instaladas × días del mes",
        "plazas_cama_noche_disponibles >= habitaciones_noche_disponibles",
        "noches_residentes + noches_no_residentes <= plazas_cama_noche_disponibles",
        "dias_operacion entre 0 y los días del mes",
        "Si hay habitaciones ocupadas debe haber noches, y viceversa",
        "Un solo reporte vigente por establecimiento y mes (un reenvío reemplaza al anterior)",
    ]

    def listas_dinamicas(self, con) -> dict:
        return {"parroquia": tuple(n for (n,) in con.execute(text(
            "SELECT nombre FROM operativo.geografia WHERE nivel = 'parroquia' ORDER BY tipo DESC, nombre")).all())}

    def reglas(self, f: dict) -> list[tuple[str, str]]:
        dias = dias_del_mes(f["periodo"])
        noches = f["noches_residentes"] + f["noches_no_residentes"]
        verificaciones = [
            (f["habitaciones_noche_ocupadas"] <= f["habitaciones_noche_disponibles"],
             "habitaciones_noche_ocupadas", "Las habitaciones ocupadas superan las disponibles"),
            (f["dias_operacion"] <= dias, "dias_operacion", f"El mes tiene {dias} días"),
            (f["habitaciones_instaladas"] > 0 and f["plazas_instaladas"] > 0,
             "habitaciones_instaladas", "La capacidad instalada debe ser mayor a 0"),
            (f["habitaciones_noche_disponibles"] <= f["habitaciones_instaladas"] * dias,
             "habitaciones_noche_disponibles", "Supera habitaciones instaladas × días del mes"),
            (f["plazas_cama_noche_disponibles"] <= f["plazas_instaladas"] * dias,
             "plazas_cama_noche_disponibles", "Supera plazas instaladas × días del mes"),
            (f["plazas_cama_noche_disponibles"] >= f["habitaciones_noche_disponibles"],
             "plazas_cama_noche_disponibles", "Las plazas no pueden ser menos que las habitaciones"),
            (noches <= f["plazas_cama_noche_disponibles"], "noches_residentes", "Las noches superan las plazas disponibles"),
            ((f["habitaciones_noche_ocupadas"] == 0) == (noches == 0),
             "habitaciones_noche_ocupadas", "Si hay habitaciones ocupadas debe haber noches, y viceversa"),
        ]
        return [(campo, mensaje) for ok, campo, mensaje in verificaciones if not ok]

    def advertencias(self, f: dict, ctx: Contexto) -> list[tuple[str, str, str]]:
        """Tipo, categoría o parroquia distintos a los del padrón: se carga igual, pero se avisa."""
        est = next(e for e in ctx.establecimientos.values() if e["id"] == f["establecimiento_id"])
        return [(campo, f[campo], f"No coincide con el registro del establecimiento ({est[campo]})")
                for campo in ("tipo_alojamiento", "categoria", "parroquia") if f[campo] != est[campo]]
