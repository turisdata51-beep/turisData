-- =============================================================================
-- 006: plantillas complementarias de carga
--
-- Reportes de los establecimientos (mismo esquema de historial que el reporte de
-- alojamiento: un reenvío marca el anterior como no vigente) y fuentes manuales de
-- otras entidades, que se guardan en operativo.observacion_externa con su carga.
-- =============================================================================

-- Qué plantilla se usó en cada carga (alojamiento, empleo, accesibilidad, consumos, series_externas)
ALTER TABLE operativo.carga_datos ADD COLUMN IF NOT EXISTS plantilla text NOT NULL DEFAULT 'alojamiento';

-- Empleo de los establecimientos, por trimestre (D3)
CREATE TABLE operativo.reporte_empleo_trimestral (
    id                 bigserial PRIMARY KEY,
    carga_id           bigint NOT NULL REFERENCES operativo.carga_datos (id),
    establecimiento_id integer NOT NULL REFERENCES operativo.establecimiento (id),
    periodo            date NOT NULL CHECK (extract(day FROM periodo) = 1 AND extract(month FROM periodo) IN (1, 4, 7, 10)),
    vigente            boolean NOT NULL DEFAULT true,
    empleo_total       integer NOT NULL CHECK (empleo_total >= 0),
    empleo_estacional  integer NOT NULL CHECK (empleo_estacional >= 0),
    empleo_mujeres     integer CHECK (empleo_mujeres >= 0),
    CHECK (empleo_estacional <= empleo_total),
    CHECK (empleo_mujeres IS NULL OR empleo_mujeres <= empleo_total)
);
CREATE UNIQUE INDEX ux_empleo_vigente ON operativo.reporte_empleo_trimestral (establecimiento_id, periodo) WHERE vigente;

-- Accesibilidad y certificaciones, por año (E1, E6)
CREATE TABLE operativo.reporte_accesibilidad_anual (
    id                           bigserial PRIMARY KEY,
    carga_id                     bigint NOT NULL REFERENCES operativo.carga_datos (id),
    establecimiento_id           integer NOT NULL REFERENCES operativo.establecimiento (id),
    anio                         integer NOT NULL CHECK (anio BETWEEN 2000 AND 2100),
    vigente                      boolean NOT NULL DEFAULT true,
    habitaciones_auditadas       integer NOT NULL CHECK (habitaciones_auditadas > 0),
    habitaciones_accesibles      integer NOT NULL CHECK (habitaciones_accesibles >= 0),
    certificacion                text,
    certificacion_vigente_hasta  date,
    CHECK (habitaciones_accesibles <= habitaciones_auditadas),
    CHECK ((certificacion IS NULL) = (certificacion_vigente_hasta IS NULL))
);
CREATE UNIQUE INDEX ux_accesibilidad_vigente ON operativo.reporte_accesibilidad_anual (establecimiento_id, anio) WHERE vigente;

-- Consumos de agua, energía y residuos, por mes (E3, E4, E5)
CREATE TABLE operativo.reporte_consumo_mensual (
    id                 bigserial PRIMARY KEY,
    carga_id           bigint NOT NULL REFERENCES operativo.carga_datos (id),
    establecimiento_id integer NOT NULL REFERENCES operativo.establecimiento (id),
    periodo            date NOT NULL CHECK (extract(day FROM periodo) = 1),
    vigente            boolean NOT NULL DEFAULT true,
    agua_m3            numeric(12, 2) CHECK (agua_m3 >= 0),
    energia_kwh        numeric(14, 2) CHECK (energia_kwh >= 0),
    residuos_kg        numeric(12, 2) CHECK (residuos_kg >= 0),
    CHECK (agua_m3 IS NOT NULL OR energia_kwh IS NOT NULL OR residuos_kg IS NOT NULL)
);
CREATE UNIQUE INDEX ux_consumo_vigente ON operativo.reporte_consumo_mensual (establecimiento_id, periodo) WHERE vigente;

-- Fuentes que se cargan con plantilla (no tienen extractor)
INSERT INTO operativo.fuente_datos (codigo, nombre, entidad_propietaria, formato, periodicidad, datos_personales,
    sla_dias, prioritaria, tipo_fuente, cobertura_geografica, variables_principales, observaciones)
VALUES
    ('plantilla_empleo_camara', 'Reporte trimestral de empleo', 'Cámara de Turismo del Azuay / asociados',
     'xlsx', 'trimestral', 'no', 120, false, 'primaria_local', 'Establecimientos asociados',
     'Empleo total, estacional y de mujeres', 'Plantilla "empleo" del panel'),
    ('plantilla_accesibilidad_camara', 'Reporte anual de accesibilidad y certificaciones', 'Cámara de Turismo del Azuay / asociados',
     'xlsx', 'anual', 'no', 400, false, 'primaria_local', 'Establecimientos asociados',
     'Habitaciones accesibles y certificaciones vigentes', 'Plantilla "accesibilidad" del panel'),
    ('plantilla_consumos_camara', 'Reporte mensual de consumos', 'Cámara de Turismo del Azuay / asociados voluntarios',
     'xlsx', 'mensual', 'no', 60, false, 'primaria_local', 'Establecimientos asociados',
     'Agua, energía y residuos', 'Plantilla "consumos" del panel'),
    ('corpac_aeropuerto', 'Pasajeros del aeropuerto Mariscal Lamar', 'Corporación Aeroportuaria de Cuenca (CORPAC)',
     'xlsx', 'mensual', 'no', 60, false, 'oficial', 'Cantón Cuenca', 'Pasajeros que llegan y salen',
     'Serie mensual por solicitud formal; se carga con la plantilla de series externas'),
    ('terminal_terrestre', 'Pasajeros de la Terminal Terrestre de Cuenca', 'Terminal Terrestre de Cuenca',
     'xlsx', 'mensual', 'no', 60, false, 'oficial', 'Cantón Cuenca', 'Pasajeros que llegan y salen',
     'Serie mensual por solicitud formal; se carga con la plantilla de series externas'),
    ('etapa_cajas', 'Visitantes del Parque Nacional Cajas', 'ETAPA EP',
     'xlsx', 'mensual', 'no', 60, false, 'oficial', 'Parque Nacional Cajas (cantón Cuenca)', 'Visitantes nacionales y extranjeros',
     'Serie mensual por solicitud formal; se carga con la plantilla de series externas'),
    ('gad_feriados', 'Balance de feriados del GAD Municipal', 'GAD Municipal de Cuenca / Fundación Turismo para Cuenca',
     'xlsx', 'evento', 'no', 400, false, 'oficial', 'Cantón Cuenca', 'Visitantes, impacto económico y ocupación por feriado',
     'Cifras de los boletines municipales; se cargan con la plantilla de series externas')
ON CONFLICT (codigo) DO NOTHING;

INSERT INTO operativo.variable_externa (codigo, nombre, unidad, descripcion, fuente_id, indicadores)
SELECT v.codigo, v.nombre, v.unidad, v.descripcion, f.id, v.indicadores
FROM (VALUES
    ('aeropuerto_pasajeros_llegada', 'Pasajeros que llegan al aeropuerto', 'pasajeros', 'Llegadas de pasajeros al aeropuerto Mariscal Lamar', 'corpac_aeropuerto', ARRAY[]::text[]),
    ('aeropuerto_pasajeros_salida', 'Pasajeros que salen del aeropuerto', 'pasajeros', 'Salidas de pasajeros del aeropuerto Mariscal Lamar', 'corpac_aeropuerto', ARRAY[]::text[]),
    ('terminal_pasajeros_llegada', 'Pasajeros que llegan a la terminal', 'pasajeros', 'Llegadas de pasajeros a la Terminal Terrestre', 'terminal_terrestre', ARRAY[]::text[]),
    ('terminal_pasajeros_salida', 'Pasajeros que salen de la terminal', 'pasajeros', 'Salidas de pasajeros de la Terminal Terrestre', 'terminal_terrestre', ARRAY[]::text[]),
    ('cajas_visitantes', 'Visitantes del Parque Nacional Cajas', 'visitantes', 'Ingresos registrados al Parque Nacional Cajas', 'etapa_cajas', ARRAY[]::text[]),
    ('feriado_visitantes', 'Visitantes en el feriado', 'visitantes', 'Visitantes estimados por el GAD Municipal en un feriado', 'gad_feriados', ARRAY['D5']),
    ('feriado_impacto_usd', 'Impacto económico del feriado', 'USD', 'Gasto estimado por el GAD Municipal en un feriado', 'gad_feriados', ARRAY['D1']),
    ('feriado_ocupacion', 'Ocupación hotelera en el feriado', '%', 'Ocupación hotelera reportada para un feriado', 'gad_feriados', ARRAY[]::text[])
) AS v (codigo, nombre, unidad, descripcion, fuente, indicadores)
JOIN operativo.fuente_datos f ON f.codigo = v.fuente
ON CONFLICT (codigo) DO NOTHING;
