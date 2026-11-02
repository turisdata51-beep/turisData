"""API HTTP: inicio de sesión, permisos por rol, filtros públicos y gestión desde el panel."""
import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.main import app
from app.nucleo.db import transaccion
from conftest import CONTRASENA, csv_reporte, fila_reporte


@pytest.fixture(scope="module")
def cliente():
    with TestClient(app) as c:
        yield c


def cabecera(cliente, rol: str) -> dict:
    r = cliente.post("/api/auth/login", json={"correo": f"{rol}@pruebas.test", "contrasena": CONTRASENA})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


def subir(cliente, rol, *filas):
    return cliente.post("/api/admin/cargas", headers=cabecera(cliente, rol),
                        files={"archivo": ("reporte.csv", csv_reporte(*filas), "text/csv")})


# --- Sesión ----------------------------------------------------------------------------------

def test_login_y_datos_del_usuario(cliente):
    r = cliente.get("/api/auth/yo", headers=cabecera(cliente, "analista"))
    assert r.status_code == 200
    assert r.json()["rol"] == "analista"
    assert "hash_contrasena" not in r.json()


def test_login_con_contrasena_incorrecta(cliente):
    r = cliente.post("/api/auth/login", json={"correo": "analista@pruebas.test", "contrasena": "equivocada"})
    assert r.status_code == 401


def test_usuario_inactivo_no_entra(cliente):
    admin = cabecera(cliente, "administrador")
    usuarios = cliente.get("/api/admin/usuarios", headers=admin).json()
    consulta = next(u for u in usuarios if u["rol"] == "consulta")
    assert cliente.patch(f"/api/admin/usuarios/{consulta['id']}", headers=admin, json={"activo": False}).status_code == 200
    r = cliente.post("/api/auth/login", json={"correo": "consulta@pruebas.test", "contrasena": CONTRASENA})
    assert r.status_code == 401


def test_token_invalido(cliente):
    assert cliente.get("/api/admin/resumen", headers={"Authorization": "Bearer basura"}).status_code == 401
    assert cliente.get("/api/admin/resumen").status_code == 401


# --- Permisos por rol --------------------------------------------------------------------------

@pytest.mark.parametrize("rol, ruta, esperado", [
    ("consulta", "/api/admin/usuarios", 403),
    ("analista", "/api/admin/usuarios", 403),
    ("asociado", "/api/admin/resumen", 403),
    ("asociado", "/api/admin/establecimientos", 403),
    ("consulta", "/api/admin/establecimientos", 403),
    ("analista", "/api/admin/auditoria", 403),
    ("administrador", "/api/admin/mis-reportes", 403),
    ("consulta", "/api/admin/resumen", 200),
    ("consulta", "/api/admin/fuentes", 200),
    ("asociado", "/api/admin/mis-reportes", 200),
    ("asociado", "/api/admin/plantillas", 200),
    ("asociado", "/api/admin/plantillas/alojamiento.xlsx", 200),
    ("asociado", "/api/admin/plantillas/series_externas.xlsx", 403),
])
def test_permisos_por_rol(cliente, rol, ruta, esperado):
    assert cliente.get(ruta, headers=cabecera(cliente, rol)).status_code == esperado


def test_consulta_no_puede_subir_archivos(cliente):
    assert subir(cliente, "consulta", fila_reporte()).status_code == 403


def test_asociado_solo_ve_sus_cargas(cliente):
    subir(cliente, "analista", fila_reporte("EST-02"))
    subir(cliente, "asociado", fila_reporte("EST-01"))
    cargas = cliente.get("/api/admin/cargas", headers=cabecera(cliente, "asociado")).json()
    assert len(cargas) == 1 and cargas[0]["usuario"] == "Asociado"


def test_administrador_no_puede_desactivarse(cliente):
    admin = cabecera(cliente, "administrador")
    yo = cliente.get("/api/auth/yo", headers=admin).json()
    r = cliente.patch(f"/api/admin/usuarios/{yo['id']}", headers=admin, json={"activo": False})
    assert r.status_code == 400


# --- Gestión ----------------------------------------------------------------------------------

def test_subir_reporte_actualiza_el_sitio_publico(cliente):
    filas = [fila_reporte(c) for c in ("EST-01", "EST-02", "EST-03")]
    r = subir(cliente, "analista", *filas)
    assert r.status_code == 200 and r.json()["estado"] == "publicada"
    resumen = cliente.get("/api/public/resumen").json()
    assert resumen["periodo"] == "2026-09-01"
    b4 = next(k for k in resumen["kpis"] if k["codigo"] == "B4")
    assert b4["valor"] == pytest.approx(50.0)


def test_archivo_demasiado_grande(cliente):
    r = cliente.post("/api/admin/cargas", headers=cabecera(cliente, "analista"),
                     files={"archivo": ("grande.csv", b"x" * (5 * 1024 * 1024 + 1), "text/csv")})
    assert r.status_code == 413


def test_crear_establecimiento_y_codigo_duplicado(cliente):
    analista = cabecera(cliente, "analista")
    nuevo = {"codigo_camara": "EST-99", "nombre_comercial": "Hotel Nuevo", "tipo_alojamiento": "Hotel",
             "categoria": "3 estrellas", "parroquia": "Yanuncay", "participa_desde": "2026-01-01"}
    assert cliente.post("/api/admin/establecimientos", headers=analista, json=nuevo).status_code == 200
    assert cliente.post("/api/admin/establecimientos", headers=analista, json=nuevo).status_code == 409
    nuevo["codigo_camara"], nuevo["parroquia"] = "EST-98", "Narnia"
    assert cliente.post("/api/admin/establecimientos", headers=analista, json=nuevo).status_code == 400


def test_asociado_necesita_establecimiento_valido(cliente):
    admin = cabecera(cliente, "administrador")
    datos = {"correo": "hotel@turisdata-pruebas.com", "nombre": "Hotel", "rol": "asociado", "contrasena": "ClaveLarga123"}
    assert cliente.post("/api/admin/usuarios", headers=admin, json=datos).status_code == 400
    datos["codigo_establecimiento"] = "EST-02"
    assert cliente.post("/api/admin/usuarios", headers=admin, json=datos).status_code == 200


def test_las_acciones_quedan_en_auditoria(cliente):
    subir(cliente, "analista", fila_reporte())
    eventos = cliente.get("/api/admin/auditoria", headers=cabecera(cliente, "administrador")).json()
    assert {"login", "carga"} <= {e["accion"] for e in eventos}


def test_fuentes_ejecutar_y_cambiar_frecuencia(cliente):
    admin = cabecera(cliente, "administrador")
    assert cliente.post("/api/admin/fuentes/plantilla_alojamiento_camara/ejecutar", headers=admin).status_code == 404
    assert cliente.post("/api/admin/fuentes/sri_ventas/ejecutar", headers=cabecera(cliente, "consulta")).status_code == 403
    assert cliente.patch("/api/admin/fuentes/sri_ventas", headers=admin, json={"frecuencia_extraccion_dias": 0}).status_code == 422
    assert cliente.patch("/api/admin/fuentes/sri_ventas", headers=admin, json={"frecuencia_extraccion_dias": 7}).status_code == 200
    assert cliente.patch("/api/admin/fuentes/no_existe", headers=admin, json={"activa": True}).status_code == 404


# --- API pública y filtros --------------------------------------------------------------------

def test_publico_sin_datos_no_falla(cliente):
    assert cliente.get("/api/public/resumen").json()["kpis"] == []
    assert cliente.get("/api/public/economia").json()["mensual"] == []


def test_filtros_publicos(cliente):
    subir(cliente, "analista", *[fila_reporte(c) for c in ("EST-01", "EST-02", "EST-03")],
          fila_reporte("EST-04", categoria="4 estrellas", parroquia="San Blas"))
    filtros = cliente.get("/api/public/filtros").json()
    assert filtros["zonas"] == ["Cuenca", "El Sagrario"]       # San Blas tiene un solo hotel
    assert filtros["categorias"] == ["3 estrellas"]            # 4 estrellas tiene un solo hotel

    zona = cliente.get("/api/public/resumen", params={"zona": "El Sagrario"}).json()
    assert {k["codigo"] for k in zona["kpis"]} >= {"A1", "B4"}
    assert "D4" not in {k["codigo"] for k in zona["kpis"]}     # D4 solo existe para el cantón

    categoria = cliente.get("/api/public/resumen", params={"categoria": "3 estrellas"}).json()
    assert next(k for k in categoria["kpis"] if k["codigo"] == "A1")["n_unidades"] == 3

    confidencial = cliente.get("/api/public/resumen", params={"zona": "San Blas"}).json()
    assert all(k["valor"] is None for k in confidencial["kpis"])
    assert cliente.get("/api/public/resumen", params={"zona": "Narnia"}).status_code == 404


def test_parroquias_marca_las_confidenciales(cliente):
    subir(cliente, "analista", *[fila_reporte(c) for c in ("EST-01", "EST-02", "EST-03")],
          fila_reporte("EST-04", categoria="4 estrellas", parroquia="San Blas"))
    parroquias = {p["parroquia"]: p for p in cliente.get("/api/public/parroquias").json()["parroquias"]}
    assert parroquias["San Blas"]["confidencial"] and "A2" not in parroquias["San Blas"]
    assert not parroquias["El Sagrario"]["confidencial"]


def test_exportar_csv_solo_publicables(cliente):
    subir(cliente, "analista", fila_reporte("EST-04", categoria="4 estrellas", parroquia="San Blas"))
    r = cliente.get("/api/admin/exportar", headers=cabecera(cliente, "consulta"))
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/csv")
    assert "San Blas" not in r.text                            # un solo hotel: no se exporta


# --- Economía, oferta y series ----------------------------------------------------------------

def insertar_externa(variable, periodo, valor, zona="Cuenca", dimensiones=None, periodicidad="mensual"):
    with transaccion() as con:
        ejecucion = con.execute(text("""INSERT INTO operativo.ejecucion_extractor (fuente_id, extractor, estado, terminada_en)
            SELECT id, 'prueba', 'ok', now() FROM operativo.fuente_datos WHERE codigo = 'sri_ventas' RETURNING id""")).scalar()
        con.execute(text("""INSERT INTO operativo.observacion_externa
            (variable, geografia_id, periodo_inicio, periodo_fin, periodicidad, dimensiones, valor, ejecucion_id)
            SELECT :v, id, :p, :p, :per, CAST(:d AS jsonb), :val, :e FROM operativo.geografia WHERE nombre = :z"""),
            dict(v=variable, p=periodo, per=periodicidad, d=json.dumps(dimensiones or {}), val=valor, z=zona, e=ejecucion))


def test_economia_calcula_acumulado_y_variaciones(cliente):
    for periodo, ventas in [("2025-01-01", 100), ("2025-02-01", 200), ("2025-03-01", 300),
                            ("2026-01-01", 110), ("2026-02-01", 240)]:
        insertar_externa("sri_ventas_seccion_i", periodo, ventas)
    e = cliente.get("/api/public/economia").json()
    assert e["ultimo"]["periodo"] == "2026-02-01"
    assert e["ultimo"]["variacion_interanual"] == 20.0           # 240 frente a 200
    assert (e["ultimo"]["acumulado"], e["ultimo"]["acumulado_anterior"]) == (350, 300)  # ene–feb de cada año
    assert e["ultimo"]["variacion_acumulada"] == pytest.approx(16.7)
    assert [(a["anio"], a["meses"]) for a in e["anual"]] == [(2025, 3), (2026, 2)]


def test_oferta_agrupa_catastro_y_capacidad(cliente):
    insertar_externa("catastro_establecimientos", "2025-02-01", 10, dimensiones={"actividad": "ALOJAMIENTO"})
    insertar_externa("catastro_establecimientos", "2025-02-01", 6, dimensiones={"actividad": "ALOJAMIENTO", "clasificacion": "HOTEL"})
    insertar_externa("catastro_establecimientos", "2025-02-01", 7, zona="El Sagrario", dimensiones={"actividad": "ALOJAMIENTO"})
    insertar_externa("hosteleria_plazas", "2025-04-01", 900)
    insertar_externa("hosteleria_plazas", "2025-04-01", 500, dimensiones={"tipo": "HOTEL"})
    o = cliente.get("/api/public/oferta").json()
    assert o["catastro"]["por_actividad"] == [{"actividad": "ALOJAMIENTO", "establecimientos": 10}]
    assert o["catastro"]["alojamiento_por_clasificacion"] == [{"clasificacion": "HOTEL", "establecimientos": 6}]
    assert o["catastro"]["alojamiento_por_parroquia"][0]["parroquia"] == "El Sagrario"
    assert o["capacidad"]["total"]["plazas"] == 900 and o["capacidad"]["por_tipo"][0]["tipo"] == "HOTEL"


def test_series_y_residencia_respetan_rango_y_zona(cliente):
    for mes_ in ("2026-08", "2026-09"):
        subir(cliente, "analista", *[fila_reporte(c, periodo=mes_) for c in ("EST-01", "EST-02", "EST-03")])
    serie = cliente.get("/api/public/series", params={"codigos": "B4,A2", "desde": "2026-09-01"}).json()
    assert [s["periodo"] for s in serie] == ["2026-09-01"] and {"B4", "A2"} <= set(serie[0])
    residencia = cliente.get("/api/public/residencia", params={"zona": "El Sagrario"}).json()
    assert residencia[-1] == {"periodo": "2026-09-01", "residente": 600.0, "no_residente": 300.0}
    assert cliente.get("/api/public/residencia", params={"codigo": "B4"}).status_code == 400


def test_sostenibilidad_publica_ultimo_dato_y_oculta_confidenciales(cliente):
    from app.servicios.plantillas import importar
    from conftest import usuario
    from test_plantillas import archivo
    filas_empleo = [dict(trimestre=t, codigo_establecimiento=c, empleo_total=10, empleo_estacional=e)
                    for t, cs in (("2026-T2", ("EST-01", "EST-02", "EST-03")), ("2026-T3", ("EST-01", "EST-02")))
                    for c, e in zip(cs, (2, 4, 6))]
    importar(archivo("empleo", *filas_empleo), "empleo.csv", usuario("analista"), "empleo")
    s = cliente.get("/api/public/sostenibilidad").json()
    assert [i["codigo"] for i in s["indicadores"]] == ["D3", "E1", "E6", "E3", "E4", "E5"]
    d3 = s["indicadores"][0]
    assert [(p["periodo"], p["valor"]) for p in d3["serie"]] == [("2026-04-01", 40.0), ("2026-07-01", None)]  # T3: 2 hoteles
    assert d3["ultimo"]["periodo"] == "2026-04-01" and d3["unidad"] == "%" and s["actualizado"]
    assert s["indicadores"][1]["ultimo"] is None and s["indicadores"][1]["serie"] == []
