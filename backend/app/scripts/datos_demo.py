"""Carga DATOS DE DEMOSTRACIÓN: 26 alojamientos ficticios con reportes de ene-2024 a sep-2026
(alojamiento mensual, empleo trimestral, accesibilidad anual y consumos mensuales).

Uso:  python -m app.scripts.datos_demo            (no hace nada si ya existen)
      python -m app.scripts.datos_demo --reiniciar (borra los datos demo y los vuelve a crear)

Los establecimientos se llaman "Alojamiento demo NN" y sus códigos empiezan con DEMO-,
para que nunca se confundan con datos reales.
"""
import calendar
import os
import random
import sys
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import text

from ..servicios.indicadores import recalcular
from ..nucleo.db import transaccion
from ..servicios.diccionario import sincronizar
from ..nucleo.seguridad import hash_contrasena

random.seed(2026)

# (tipo, categoría, habitaciones, parroquia, tarifa base USD, desde)
ALOJAMIENTOS = [
    ("Hotel", "5 estrellas", 110, "El Sagrario", 118, "2024-01"),
    ("Hotel", "5 estrellas", 85, "El Batán", 105, "2024-01"),
    ("Hotel", "4 estrellas", 62, "El Sagrario", 78, "2024-01"),
    ("Hotel", "4 estrellas", 48, "Gil Ramírez Dávalos", 72, "2024-01"),
    ("Hotel", "4 estrellas", 55, "Huayna Cápac", 70, "2024-01"),
    ("Hotel", "4 estrellas", 40, "San Sebastián", 74, "2024-01"),
    ("Hotel", "3 estrellas", 34, "El Sagrario", 52, "2024-01"),
    ("Hotel", "3 estrellas", 30, "San Blas", 48, "2024-01"),
    ("Hotel", "3 estrellas", 28, "Gil Ramírez Dávalos", 47, "2024-01"),
    ("Hotel", "3 estrellas", 36, "Bellavista", 45, "2024-01"),
    ("Hotel", "3 estrellas", 25, "Sucre", 44, "2024-01"),
    ("Hostal", "3 estrellas", 18, "El Sagrario", 38, "2024-01"),
    ("Hostal", "3 estrellas", 16, "San Blas", 36, "2024-01"),
    ("Hostal", "2 estrellas", 14, "Gil Ramírez Dávalos", 28, "2024-01"),
    ("Hostal", "2 estrellas", 12, "San Sebastián", 27, "2024-01"),
    ("Hostal", "2 estrellas", 15, "El Vecino", 26, "2024-01"),
    ("Hostal", "1 estrella", 10, "San Blas", 22, "2024-01"),
    ("Hostería", "4 estrellas", 30, "Baños", 85, "2024-01"),
    ("Hostería", "3 estrellas", 22, "Baños", 60, "2024-01"),
    ("Hostería", "3 estrellas", 20, "Baños", 58, "2024-01"),
    ("Hotel", "4 estrellas", 44, "Yanuncay", 68, "2024-01"),
    ("Casa de huéspedes", "Categoría única", 6, "El Sagrario", 35, "2024-01"),
    ("Hotel", "4 estrellas", 52, "El Batán", 76, "2025-01"),
    ("Hostal", "3 estrellas", 16, "El Sagrario", 37, "2025-01"),
    ("Hotel", "3 estrellas", 32, "Huayna Cápac", 50, "2025-06"),
    ("Hostería", "Categoría única", 12, "Turi", 55, "2026-01"),
]

# Ocupación base por mes (Cuenca): feriados de Carnaval, Semana Santa, 10 de Agosto,
# Independencia de Cuenca (3 nov) y fin de año suben la demanda.
OCUPACION_MES = {1: .50, 2: .58, 3: .55, 4: .58, 5: .50, 6: .54, 7: .64, 8: .68, 9: .52, 10: .56, 11: .70, 12: .66}
CARNAVAL = {2024: 2, 2025: 3, 2026: 2}
SEMANA_SANTA = {2024: 3, 2025: 4, 2026: 4}
NO_RESIDENTES_MES = {1: .34, 2: .30, 3: .33, 4: .30, 5: .36, 6: .40, 7: .44, 8: .42, 9: .38, 10: .36, 11: .30, 12: .33}


def _meses(desde: date, hasta: date):
    actual = desde
    while actual <= hasta:
        yield actual
        actual = date(actual.year + actual.month // 12, actual.month % 12 + 1, 1)


def _reporte(hab, tarifa, periodo: date, factor_hotel: float):
    dias = calendar.monthrange(periodo.year, periodo.month)[1]
    ocupacion = OCUPACION_MES[periodo.month]
    if CARNAVAL[periodo.year] == periodo.month:
        ocupacion += .08
    if SEMANA_SANTA[periodo.year] == periodo.month:
        ocupacion += .05
    ocupacion *= (1 + .04 * (periodo.year - 2024)) * factor_hotel * random.uniform(.92, 1.08)
    ocupacion = min(ocupacion, .95)

    cerradas = random.choice([0, 0, 0, 0, 1, 2]) if hab > 20 else 0
    disponibles = (hab - cerradas) * dias
    ocupadas = round(disponibles * ocupacion)
    plazas = round(hab * random.uniform(2.0, 2.4))
    plazas_noche = round(disponibles * plazas / hab)
    noches = min(round(ocupadas * random.uniform(1.5, 1.8)), plazas_noche)
    no_res = NO_RESIDENTES_MES[periodo.month] * random.uniform(.85, 1.15)
    noches_nr = round(noches * no_res)
    noches_r = noches - noches_nr
    llegadas_r = max(1, round(noches_r / random.uniform(1.7, 2.1)))
    llegadas_nr = max(1, round(noches_nr / random.uniform(2.3, 2.9))) if noches_nr else 0
    adr = tarifa * (1 + .2 * (ocupacion - .55)) * (1 + .03 * (periodo.year - 2024)) * random.uniform(.95, 1.05)
    return dict(
        habitaciones_instaladas=hab, plazas_instaladas=plazas, dias_operacion=dias,
        habitaciones_noche_disponibles=disponibles, habitaciones_noche_ocupadas=ocupadas,
        plazas_cama_noche_disponibles=plazas_noche, llegadas_residentes=llegadas_r,
        llegadas_no_residentes=llegadas_nr, noches_residentes=noches_r, noches_no_residentes=noches_nr,
        ingreso=round(ocupadas * adr, 2))


TABLAS_DE_REPORTES = ("operativo.reporte_alojamiento_mensual", "operativo.reporte_empleo_trimestral",
                      "operativo.reporte_accesibilidad_anual", "operativo.reporte_consumo_mensual")


def _carga(con, plantilla: str, fuente: str, nombre: str, filas: int) -> int:
    return con.execute(text("""
        INSERT INTO operativo.carga_datos (fuente_id, mecanismo, nombre_archivo, version_plantilla, plantilla,
          registros_recibidos, registros_validos, estado)
        SELECT id, 'archivo', :n, 'v1', :p, :k, :k, 'publicada' FROM operativo.fuente_datos WHERE codigo = :f
        RETURNING id"""), dict(n=nombre, p=plantilla, k=filas, f=fuente)).scalar()


def _complementarios(con, hoteles, noches_por_reporte):
    """Empleo por trimestre, accesibilidad por año y consumos por mes (estos solo en ~60 % de los hoteles)."""
    empleo = []
    for est_id, hab, _tarifa, inicio, _factor, _ingreso in hoteles:
        for anio in (2024, 2025, 2026):
            for trimestre in range(1, 5):
                periodo = date(anio, (trimestre - 1) * 3 + 1, 1)
                if periodo < inicio or periodo > date(2026, 7, 1) or random.random() < .08:
                    continue
                total = max(2, round(hab * random.uniform(.45, .7)))
                temporada = .28 if trimestre in (3, 4) else .14  # vacaciones de la Sierra y fin de año
                estacional = min(total, round(total * temporada * random.uniform(.7, 1.3)))
                empleo.append(dict(e=est_id, p=periodo, t=total, s=estacional, m=round(total * random.uniform(.4, .6))))
    carga = _carga(con, "empleo", "plantilla_empleo_camara", "demo_empleo.xlsx", len(empleo))
    con.execute(text("""INSERT INTO operativo.reporte_empleo_trimestral
        (carga_id, establecimiento_id, periodo, empleo_total, empleo_estacional, empleo_mujeres)
        VALUES (:c, :e, :p, :t, :s, :m)"""), [{**f, "c": carga} for f in empleo])

    accesibilidad = []
    for est_id, hab, _tarifa, inicio, _factor, _ingreso in hoteles:
        certificado = random.random() < .35
        for anio in (2024, 2025, 2026):
            if anio < inicio.year:
                continue
            accesibles = max(0, round(hab * random.uniform(0, .06)))
            vence = date(anio + 1, random.randint(1, 12), 1) if certificado else None
            accesibilidad.append(dict(e=est_id, a=anio, h=hab, x=accesibles,
                                      c="Certificación de calidad (demo)" if certificado else None, v=vence))
    carga = _carga(con, "accesibilidad", "plantilla_accesibilidad_camara", "demo_accesibilidad.xlsx", len(accesibilidad))
    con.execute(text("""INSERT INTO operativo.reporte_accesibilidad_anual
        (carga_id, establecimiento_id, anio, habitaciones_auditadas, habitaciones_accesibles, certificacion,
         certificacion_vigente_hasta) VALUES (:c, :e, :a, :h, :x, :cert, :v)"""),
        [{**f, "c": carga, "cert": f["c"]} for f in accesibilidad])

    voluntarios = {h[0] for h in hoteles if random.random() < .6}
    consumos = [dict(e=e, p=p, agua=round(n * random.uniform(.2, .32), 2), energia=round(n * random.uniform(9, 15), 2),
                     residuos=round(n * random.uniform(.7, 1.2), 2))
                for (e, p), n in noches_por_reporte.items() if e in voluntarios and n > 0]
    carga = _carga(con, "consumos", "plantilla_consumos_camara", "demo_consumos.xlsx", len(consumos))
    con.execute(text("""INSERT INTO operativo.reporte_consumo_mensual
        (carga_id, establecimiento_id, periodo, agua_m3, energia_kwh, residuos_kg)
        VALUES (:c, :e, :p, :agua, :energia, :residuos)"""), [{**f, "c": carga} for f in consumos])


def _usuario(con, correo_var, contrasena_var, nombre, rol, establecimiento_id=None):
    correo, contrasena = os.environ.get(correo_var), os.environ.get(contrasena_var)
    if not correo or not contrasena:
        return
    con.execute(text("""
        INSERT INTO operativo.usuario (correo, nombre, hash_contrasena, rol, establecimiento_id)
        VALUES (:c, :n, :h, :r, :e) ON CONFLICT (correo) DO NOTHING"""),
        dict(c=correo.lower(), n=nombre, h=hash_contrasena(contrasena), r=rol, e=establecimiento_id))


def main():
    reiniciar = "--reiniciar" in sys.argv
    sincronizar()
    with transaccion() as con:
        existe = con.execute(text("SELECT count(*) FROM operativo.establecimiento WHERE codigo_camara LIKE 'DEMO-%'")).scalar()
        if existe and not reiniciar:
            print("Los datos demo ya existen. Use --reiniciar para regenerarlos.")
            return
        if existe:
            demo = "SELECT id FROM operativo.establecimiento WHERE codigo_camara LIKE 'DEMO-%'"
            usuarios_demo = f"SELECT id FROM operativo.usuario WHERE establecimiento_id IN ({demo})"
            ids = [r[0] for r in con.execute(text(
                " UNION ".join(f"SELECT carga_id FROM {t} WHERE establecimiento_id IN ({demo})" for t in TABLAS_DE_REPORTES)
                + f" UNION SELECT id FROM operativo.carga_datos WHERE usuario_id IN ({usuarios_demo})"))]
            for tabla in TABLAS_DE_REPORTES:
                con.execute(text(f"DELETE FROM {tabla} WHERE establecimiento_id IN ({demo})"))
            if ids:
                for tabla in TABLAS_DE_REPORTES:
                    con.execute(text(f"DELETE FROM {tabla} WHERE carga_id = ANY(:i)"), dict(i=ids))
                con.execute(text("DELETE FROM operativo.carga_error WHERE carga_id = ANY(:i)"), dict(i=ids))
                con.execute(text("DELETE FROM operativo.carga_datos WHERE id = ANY(:i)"), dict(i=ids))
            con.execute(text(f"UPDATE operativo.auditoria SET usuario_id = NULL WHERE usuario_id IN ({usuarios_demo})"))
            con.execute(text(f"DELETE FROM operativo.usuario WHERE establecimiento_id IN ({demo})"))
            con.execute(text("DELETE FROM operativo.establecimiento WHERE codigo_camara LIKE 'DEMO-%'"))

        parroquias = dict(con.execute(text("SELECT nombre, id FROM operativo.geografia WHERE nivel = 'parroquia'")).all())
        fuente = con.execute(text("SELECT id FROM operativo.fuente_datos WHERE codigo = 'plantilla_alojamiento_camara'")).scalar()

        hoteles = []
        for i, (tipo, cat, hab, parroquia, tarifa, desde) in enumerate(ALOJAMIENTOS, start=1):
            codigo = f"DEMO-{i:03d}"
            inicio = date.fromisoformat(desde + "-01")
            est_id = con.execute(text("""
                INSERT INTO operativo.establecimiento
                  (codigo_camara, nombre_comercial, tipo_alojamiento, categoria, parroquia_id, participa_desde)
                VALUES (:c, :n, :t, :cat, :p, :d) RETURNING id"""),
                dict(c=codigo, n=f"Alojamiento demo {i:02d}", t=tipo, cat=cat, p=parroquias[parroquia], d=inicio)).scalar()
            hoteles.append((est_id, hab, tarifa, inicio, random.uniform(.85, 1.15), random.random() < .7))

        noches_por_reporte = {}  # (establecimiento, mes) -> noches, para los consumos
        for periodo in _meses(date(2024, 1, 1), date(2026, 9, 1)):
            siguiente = date(periodo.year + periodo.month // 12, periodo.month % 12 + 1, 1)
            recibido = datetime.combine(siguiente + timedelta(days=random.randint(5, 12)), datetime.min.time(),
                                        tzinfo=timezone.utc) + timedelta(hours=15)
            filas = []
            for est_id, hab, tarifa, inicio, factor, reporta_ingreso in hoteles:
                if periodo < inicio or random.random() < .06:  # algunos meses un hotel no reporta
                    continue
                r = _reporte(hab, tarifa, periodo, factor)
                r.update(establecimiento_id=est_id, periodo=periodo,
                         ingreso=r["ingreso"] if reporta_ingreso else None)
                filas.append(r)
                noches_por_reporte[(est_id, periodo)] = r["noches_residentes"] + r["noches_no_residentes"]
            carga_id = con.execute(text("""
                INSERT INTO operativo.carga_datos (fuente_id, mecanismo, nombre_archivo, version_plantilla, recibido_en,
                  registros_recibidos, registros_validos, campos_criticos_esperados, campos_criticos_validos, estado)
                VALUES (:f, 'archivo', :n, 'v1', :t, :k, :k, :ce, :ce, 'publicada') RETURNING id"""),
                dict(f=fuente, n=f"demo_{periodo:%Y-%m}.xlsx", t=recibido, k=len(filas), ce=len(filas) * 15)).scalar()
            con.execute(text("""
                INSERT INTO operativo.reporte_alojamiento_mensual
                  (carga_id, establecimiento_id, periodo, habitaciones_instaladas, plazas_instaladas, dias_operacion,
                   habitaciones_noche_disponibles, habitaciones_noche_ocupadas, plazas_cama_noche_disponibles,
                   llegadas_residentes, llegadas_no_residentes, noches_residentes, noches_no_residentes,
                   ingreso_habitaciones_usd)
                VALUES (:carga_id, :establecimiento_id, :periodo, :habitaciones_instaladas, :plazas_instaladas,
                   :dias_operacion, :habitaciones_noche_disponibles, :habitaciones_noche_ocupadas,
                   :plazas_cama_noche_disponibles, :llegadas_residentes, :llegadas_no_residentes,
                   :noches_residentes, :noches_no_residentes, :ingreso)"""),
                [{**f, "carga_id": carga_id} for f in filas])

        _complementarios(con, hoteles, noches_por_reporte)

        _usuario(con, "ADMIN_CORREO", "ADMIN_CONTRASENA", "Administrador", "administrador")
        _usuario(con, "DEMO_ANALISTA_CORREO", "DEMO_ANALISTA_CONTRASENA", "Analista demo", "analista")
        _usuario(con, "DEMO_CONSULTA_CORREO", "DEMO_CONSULTA_CONTRASENA", "Consulta demo", "consulta")
        _usuario(con, "DEMO_ASOCIADO_CORREO", "DEMO_ASOCIADO_CONTRASENA", "Alojamiento demo 01", "asociado", hoteles[0][0])

    print(f"Observaciones calculadas: {recalcular()}")


if __name__ == "__main__":
    main()
