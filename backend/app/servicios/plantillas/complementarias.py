"""Plantillas complementarias de los establecimientos: empleo, accesibilidad y consumos."""
from .base import Columna, Plantilla


class Empleo(Plantilla):
    """D3: participación del empleo estacional."""
    codigo = "empleo"
    nombre = "Reporte trimestral de empleo"
    descripcion = "Personas que trabajan en cada establecimiento durante el trimestre."
    unidad = "establecimiento y trimestre"
    fuente_codigo = "plantilla_empleo_camara"
    tabla = "operativo.reporte_empleo_trimestral"
    columnas = [
        Columna("trimestre", "trimestre", "Trimestre reportado en formato AAAA-T1 a AAAA-T4 (ej. 2026-T3)."),
        Columna("codigo_establecimiento", "establecimiento", "Código asignado por la Cámara."),
        Columna("empleo_total", "entero", "Personas que trabajaron en el trimestre (promedio del trimestre)."),
        Columna("empleo_estacional", "entero", "De ellas, cuántas fueron contratadas solo por temporada."),
        Columna("empleo_mujeres", "entero", "OPCIONAL. De ellas, cuántas son mujeres.", obligatoria=False),
    ]
    reglas_texto = [
        "empleo_estacional <= empleo_total",
        "empleo_mujeres <= empleo_total",
        "Un solo reporte vigente por establecimiento y trimestre",
    ]

    def reglas(self, f):
        errores = []
        if f["empleo_estacional"] > f["empleo_total"]:
            errores.append(("empleo_estacional", "El empleo estacional supera el empleo total"))
        if f["empleo_mujeres"] is not None and f["empleo_mujeres"] > f["empleo_total"]:
            errores.append(("empleo_mujeres", "El empleo de mujeres supera el empleo total"))
        return errores


class Accesibilidad(Plantilla):
    """E1: habitaciones accesibles. E6: establecimientos con certificación vigente."""
    codigo = "accesibilidad"
    nombre = "Reporte anual de accesibilidad y certificaciones"
    descripcion = "Habitaciones adaptadas para personas con discapacidad y certificaciones de calidad o sostenibilidad."
    unidad = "establecimiento y año"
    fuente_codigo = "plantilla_accesibilidad_camara"
    tabla = "operativo.reporte_accesibilidad_anual"
    clave_periodo = "anio"
    columnas = [
        Columna("anio", "anio", "Año reportado (ej. 2026)."),
        Columna("codigo_establecimiento", "establecimiento", "Código asignado por la Cámara."),
        Columna("habitaciones_auditadas", "entero", "Habitaciones revisadas con el criterio de accesibilidad."),
        Columna("habitaciones_accesibles", "entero", "De ellas, cuántas son accesibles para personas con discapacidad."),
        Columna("certificacion", "texto", "OPCIONAL. Nombre de la certificación vigente (calidad, sostenibilidad o responsabilidad social).", obligatoria=False),
        Columna("certificacion_vigente_hasta", "fecha", "OPCIONAL. Fecha de vencimiento de la certificación (AAAA-MM-DD).", obligatoria=False),
    ]
    reglas_texto = [
        "habitaciones_accesibles <= habitaciones_auditadas",
        "Si hay certificación, debe tener fecha de vencimiento, y viceversa",
    ]

    def reglas(self, f):
        errores = []
        if f["habitaciones_auditadas"] == 0:
            errores.append(("habitaciones_auditadas", "Debe haber al menos una habitación auditada"))
        if f["habitaciones_accesibles"] > f["habitaciones_auditadas"]:
            errores.append(("habitaciones_accesibles", "Las habitaciones accesibles superan las auditadas"))
        if (f["certificacion"] is None) != (f["certificacion_vigente_hasta"] is None):
            errores.append(("certificacion_vigente_hasta", "La certificación y su fecha de vencimiento van juntas"))
        return errores


class Consumos(Plantilla):
    """E3, E4, E5: agua, energía y residuos por noche turística."""
    codigo = "consumos"
    nombre = "Reporte mensual de consumos"
    descripcion = "Agua, energía y residuos del establecimiento en el mes, según sus facturas o registros."
    unidad = "establecimiento y mes"
    fuente_codigo = "plantilla_consumos_camara"
    tabla = "operativo.reporte_consumo_mensual"
    columnas = [
        Columna("periodo", "mes", "Mes reportado en formato AAAA-MM."),
        Columna("codigo_establecimiento", "establecimiento", "Código asignado por la Cámara."),
        Columna("agua_m3", "decimal", "Agua consumida en el mes, en metros cúbicos (planilla de ETAPA).", obligatoria=False),
        Columna("energia_kwh", "decimal", "Energía eléctrica consumida en el mes, en kWh (planilla de Centrosur).", obligatoria=False),
        Columna("residuos_kg", "decimal", "Residuos generados en el mes, en kilogramos (pesaje propio o registro de EMAC).", obligatoria=False),
    ]
    reglas_texto = [
        "Al menos uno de los tres consumos",
        "Los consumos por noche se calculan con las noches del reporte de alojamiento del mismo mes",
    ]

    def reglas(self, f):
        if all(f[c] is None for c in ("agua_m3", "energia_kwh", "residuos_kg")):
            return [("agua_m3", "Reporte al menos uno de los consumos")]
        return []
