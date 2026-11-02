"""Series de otras entidades que no publican en la web: aeropuerto, terminal, Cajas y feriados.

Se guardan en operativo.observacion_externa, igual que lo que traen los extractores,
pero ligadas a la carga en vez de a una ejecución. Si se vuelve a cargar un valor
distinto para la misma variable, zona y período, el anterior queda como no vigente.
"""
from sqlalchemy import text

from .base import Columna, Plantilla

PERIODICIDADES = ("mensual", "trimestral", "anual", "feriado", "evento")


class SeriesExternas(Plantilla):
    codigo = "series_externas"
    nombre = "Series de otras entidades"
    descripcion = ("Datos que entregan el aeropuerto, la Terminal Terrestre, ETAPA (Parque Nacional Cajas) o el GAD "
                   "Municipal (balance de feriados) y que no se pueden extraer de la web.")
    unidad = "variable, zona y período"
    fuente_codigo = "gad_feriados"  # la carga se registra aquí; cada dato queda con su variable y su fuente
    roles = ("administrador", "analista")
    clave_periodo = "periodo_inicio"
    columnas = [
        Columna("variable", "lista", "Qué se mide (ver la hoja Listas)."),
        Columna("zona", "zona", "Cuenca, o el nombre de una parroquia."),
        Columna("periodicidad", "lista", "mensual, trimestral, anual, feriado o evento.", opciones=PERIODICIDADES),
        Columna("periodo_inicio", "fecha", "Primer día del período (AAAA-MM-DD). Para un mes: el día 1."),
        Columna("periodo_fin", "fecha", "Último día del período (AAAA-MM-DD)."),
        Columna("evento", "texto", "Nombre del feriado o evento (ej. Carnaval 2026). Obligatorio para feriados y eventos.", obligatoria=False),
        Columna("valor", "decimal", "Cifra reportada por la entidad, en la unidad de la variable."),
    ]
    reglas_texto = [
        "periodo_fin >= periodo_inicio",
        "Los feriados y eventos necesitan su nombre en la columna evento",
        "Si se carga otro valor para la misma variable, zona y período, el anterior se conserva como no vigente",
    ]

    def listas_dinamicas(self, con) -> dict:
        return {"variable": tuple(v for (v,) in con.execute(text("""
            SELECT v.codigo FROM operativo.variable_externa v JOIN operativo.fuente_datos f ON f.id = v.fuente_id
            WHERE f.extractor IS NULL AND f.tipo_fuente = 'oficial' ORDER BY v.codigo""")).all())}

    def reglas(self, f):
        errores = []
        if f["periodo_fin"] < f["periodo_inicio"]:
            errores.append(("periodo_fin", "El período termina antes de empezar"))
        if f["periodicidad"] in ("feriado", "evento") and not f["evento"]:
            errores.append(("evento", "Indique el nombre del feriado o evento"))
        return errores

    def clave_duplicado(self, f):
        return f["variable"], f["zona"], f["periodo_inicio"], f["periodicidad"], f["evento"] or ""

    def guardar(self, con, filas, carga_id):
        for f in filas:
            clave = dict(v=f["variable"], g=f["zona"], ini=f["periodo_inicio"], per=f["periodicidad"], ev=f["evento"] or "")
            actual = con.execute(text("""
                SELECT id, valor FROM operativo.observacion_externa
                WHERE variable = :v AND geografia_id = :g AND periodo_inicio = :ini AND periodicidad = :per
                  AND coalesce(evento, '') = :ev AND dimensiones = '{}'::jsonb AND vigente"""), clave).first()
            if actual and float(actual.valor) == float(f["valor"]):
                continue
            if actual:
                con.execute(text("UPDATE operativo.observacion_externa SET vigente = false WHERE id = :id"), dict(id=actual.id))
            con.execute(text("""
                INSERT INTO operativo.observacion_externa
                  (variable, geografia_id, periodo_inicio, periodo_fin, periodicidad, evento, valor, carga_id)
                VALUES (:v, :g, :ini, :fin, :per, NULLIF(:ev, ''), :valor, :carga)"""),
                {**clave, "fin": f["periodo_fin"], "valor": f["valor"], "carga": carga_id})
