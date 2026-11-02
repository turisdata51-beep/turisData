"""Marco de extractores y programador, sin internet: la descarga se reemplaza por datos fijos."""
import json
from datetime import date
from urllib.robotparser import RobotFileParser

import pytest
from sqlalchemy import text

from app.extractores.base import Dato, Extractor, FuenteNoPermitida, ejecucion_en_curso
from app.nucleo.db import transaccion
from app.servicios import programador


class ExtractorDePrueba(Extractor):
    """Usa la fuente sri_ventas; 'descarga' el JSON que se le indique."""
    fuente_codigo = "sri_ventas"
    url = "https://ejemplo.test/datos"

    def __init__(self, valores: dict, zona="Cuenca"):
        super().__init__()
        self.valores, self.zona = valores, zona

    def descargar(self) -> bytes:
        return json.dumps(self.valores, sort_keys=True).encode()

    def interpretar(self, contenido: bytes) -> list[Dato]:
        return [Dato("sri_ventas_seccion_i", date.fromisoformat(p), date.fromisoformat(p), v, geografia=self.zona)
                for p, v in json.loads(contenido).items()]


def historial():
    with transaccion() as con:
        return [dict(r) for r in con.execute(text("""
            SELECT periodo_inicio, valor, vigente FROM operativo.observacion_externa ORDER BY id""")).mappings()]


def ejecuciones():
    with transaccion() as con:
        return [dict(r) for r in con.execute(text(
            "SELECT estado, registros_nuevos, registros_actualizados, mensaje FROM operativo.ejecucion_extractor ORDER BY id")).mappings()]


def test_primera_ejecucion_guarda_los_datos():
    r = ExtractorDePrueba({"2026-01-01": 100, "2026-02-01": 200}).ejecutar()
    assert (r["estado"], r["nuevos"], r["actualizados"]) == ("ok", 2, 0)
    assert len(historial()) == 2


def test_fuente_sin_cambios_no_se_vuelve_a_procesar():
    ExtractorDePrueba({"2026-01-01": 100}).ejecutar()
    r = ExtractorDePrueba({"2026-01-01": 100}).ejecutar()
    assert r["estado"] == "sin_cambios"
    assert len(historial()) == 1


def test_valor_corregido_conserva_la_version_anterior():
    ExtractorDePrueba({"2026-01-01": 100}).ejecutar()
    r = ExtractorDePrueba({"2026-01-01": 150, "2026-02-01": 200}).ejecutar()
    assert (r["nuevos"], r["actualizados"]) == (1, 1)
    enero = [h for h in historial() if h["periodo_inicio"] == date(2026, 1, 1)]
    assert [(float(h["valor"]), h["vigente"]) for h in enero] == [(100, False), (150, True)]


def test_forzar_reprocesa_aunque_no_cambie():
    ExtractorDePrueba({"2026-01-01": 100}).ejecutar()
    assert ExtractorDePrueba({"2026-01-01": 100}).ejecutar(forzar=True)["estado"] == "ok"


def test_zona_desconocida_se_informa_sin_detener_la_carga():
    r = ExtractorDePrueba({"2026-01-01": 100}, zona="Atlántida").ejecutar()
    assert r["estado"] == "ok" and r["nuevos"] == 0
    assert "Atlántida" in r["mensaje"]


def test_error_de_la_fuente_queda_registrado():
    class Rota(ExtractorDePrueba):
        def descargar(self):
            raise ValueError("el sitio cambió de formato")

    r = Rota({}).ejecutar()
    assert r["estado"] == "error"
    assert ejecuciones()[-1]["mensaje"] == "ValueError: el sitio cambió de formato"


def test_respeta_robots_txt():
    extractor = ExtractorDePrueba({})
    robots = RobotFileParser()
    robots.parse(["User-agent: *", "Disallow: /privado/", "Crawl-delay: 10"])
    extractor._robots["https://ejemplo.test"] = robots
    assert extractor.permitido("https://ejemplo.test/datos")
    assert not extractor.permitido("https://ejemplo.test/privado/archivo.csv")
    with pytest.raises(FuenteNoPermitida):
        extractor.obtener("https://ejemplo.test/privado/archivo.csv")


def test_recalcula_indicadores_solo_si_llegan_datos_nuevos(monkeypatch):
    import app.servicios.indicadores as indicadores
    llamadas = []
    monkeypatch.setattr(indicadores, "recalcular", lambda: llamadas.append(1))
    ExtractorDePrueba({"2026-01-01": 100}).ejecutar()       # nuevo: recalcula
    ExtractorDePrueba({"2026-01-01": 100}).ejecutar()       # sin cambios: no recalcula
    assert len(llamadas) == 1


def test_ejecucion_en_curso_bloquea_otra():
    with transaccion() as con:
        con.execute(text("""INSERT INTO operativo.ejecucion_extractor (fuente_id, extractor, estado)
            SELECT id, 'x', 'en_curso' FROM operativo.fuente_datos WHERE codigo = 'sri_ventas'"""))
    assert ejecucion_en_curso("sri_ventas")
    assert not ejecucion_en_curso("catastro_turistico")


def test_ejecucion_abandonada_no_bloquea():
    with transaccion() as con:
        con.execute(text("""INSERT INTO operativo.ejecucion_extractor (fuente_id, extractor, estado, iniciada_en)
            SELECT id, 'x', 'en_curso', now() - interval '3 hours' FROM operativo.fuente_datos WHERE codigo = 'sri_ventas'"""))
    assert not ejecucion_en_curso("sri_ventas")


# --- Programador -------------------------------------------------------------------------------

def registrar_ejecucion(fuente: str, hace_dias: int, estado="ok"):
    with transaccion() as con:
        con.execute(text("""INSERT INTO operativo.ejecucion_extractor (fuente_id, extractor, estado, iniciada_en)
            SELECT id, 'x', :e, now() - make_interval(days => :d) FROM operativo.fuente_datos WHERE codigo = :f"""),
            dict(e=estado, d=hace_dias, f=fuente))


def test_sin_ejecuciones_todas_las_fuentes_estan_pendientes():
    assert set(programador.fuentes_pendientes()) == {"sri_ventas", "catastro_turistico", "hosteleria_cuenca", "inec_poblacion"}


def test_pendientes_segun_su_frecuencia():
    registrar_ejecucion("sri_ventas", 3)             # cada 7 días: al día
    registrar_ejecucion("catastro_turistico", 31)    # cada 30 días: vencida
    registrar_ejecucion("hosteleria_cuenca", 1, estado="error")  # un error no cuenta como actualización
    registrar_ejecucion("inec_poblacion", 10)        # cada 90 días: al día
    assert set(programador.fuentes_pendientes()) == {"catastro_turistico", "hosteleria_cuenca"}


def test_fuente_desactivada_no_se_programa():
    with transaccion() as con:
        con.execute(text("UPDATE operativo.fuente_datos SET activa = false WHERE codigo = 'inec_poblacion'"))
    try:
        assert "inec_poblacion" not in programador.fuentes_pendientes()
    finally:
        with transaccion() as con:
            con.execute(text("UPDATE operativo.fuente_datos SET activa = true WHERE codigo = 'inec_poblacion'"))


def test_ejecutar_pendientes_corre_cada_extractor(monkeypatch):
    llamadas = []

    class Falso:
        fuente_codigo = "sri_ventas"

        def ejecutar(self):
            llamadas.append("sri_ventas")
            return {"estado": "ok", "mensaje": "prueba", "nuevos": 0, "actualizados": 0}

    monkeypatch.setattr(programador, "fuentes_pendientes", lambda: ["sri_ventas"])
    monkeypatch.setitem(programador.EXTRACTORES, "sri_ventas", Falso)
    resultados = programador.ejecutar_pendientes()
    assert llamadas == ["sri_ventas"] and resultados[0]["extractor"] == "sri_ventas"


def test_programador_se_desactiva_por_entorno(monkeypatch):
    monkeypatch.setenv("EXTRACCION_AUTOMATICA", "0")
    assert not programador.activo()
    monkeypatch.setenv("EXTRACCION_AUTOMATICA", "1")
    assert programador.activo()
