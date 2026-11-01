-- =============================================================================
-- 004: histórico de datos obtenidos de fuentes externas (scraping, descargas, APIs)
--
-- Cada extractor guarda observaciones con el mismo formato: fuente + variable +
-- geografía + período + valor. Nada se sobreescribe sin dejar rastro: si una
-- fuente corrige un dato, la versión anterior queda marcada como no vigente.
-- =============================================================================

-- Catálogo de variables externas (lo que publica cada fuente)
CREATE TABLE operativo.variable_externa (
    codigo       text PRIMARY KEY,           -- ej. aeropuerto_pasajeros_llegada
    nombre       text NOT NULL,
    unidad       text NOT NULL,
    descripcion  text,
    fuente_id    integer NOT NULL REFERENCES operativo.fuente_datos (id),
    indicadores  text[] NOT NULL DEFAULT '{}' -- indicadores del manual que alimenta (ej. {D5})
);

-- Cada vez que corre un extractor
CREATE TABLE operativo.ejecucion_extractor (
    id              bigserial PRIMARY KEY,
    fuente_id       integer NOT NULL REFERENCES operativo.fuente_datos (id),
    extractor       text NOT NULL,           -- nombre del módulo Python
    iniciada_en     timestamptz NOT NULL DEFAULT now(),
    terminada_en    timestamptz,
    estado          text NOT NULL DEFAULT 'en_curso'
                    CHECK (estado IN ('en_curso', 'ok', 'sin_cambios', 'error')),
    url_origen      text,
    hash_contenido  text,                    -- detecta si la fuente cambió desde la última vez
    registros_nuevos      integer NOT NULL DEFAULT 0,
    registros_actualizados integer NOT NULL DEFAULT 0,
    mensaje         text,
    usuario_id      integer REFERENCES operativo.usuario (id)  -- null si fue programada
);
CREATE INDEX ix_ejecucion_fuente ON operativo.ejecucion_extractor (fuente_id, iniciada_en DESC);

-- Observaciones históricas de fuentes externas
CREATE TABLE operativo.observacion_externa (
    id              bigserial PRIMARY KEY,
    variable        text NOT NULL REFERENCES operativo.variable_externa (codigo),
    geografia_id    integer NOT NULL REFERENCES operativo.geografia (id),
    periodo_inicio  date NOT NULL,
    periodo_fin     date NOT NULL,
    periodicidad    text NOT NULL CHECK (periodicidad IN ('diaria', 'semanal', 'mensual', 'trimestral', 'anual', 'feriado', 'evento')),
    evento          text,                    -- ej. 'Carnaval 2026' cuando periodicidad = feriado
    dimensiones     jsonb NOT NULL DEFAULT '{}'::jsonb,
    valor           numeric NOT NULL,
    vigente         boolean NOT NULL DEFAULT true,
    ejecucion_id    bigint REFERENCES operativo.ejecucion_extractor (id),
    carga_id        bigint REFERENCES operativo.carga_datos (id),   -- si vino de una carga manual
    capturado_en    timestamptz NOT NULL DEFAULT now(),
    CHECK (periodo_fin >= periodo_inicio),
    CHECK (ejecucion_id IS NOT NULL OR carga_id IS NOT NULL)
);
CREATE UNIQUE INDEX ux_observacion_externa_vigente
    ON operativo.observacion_externa (variable, geografia_id, periodo_inicio, periodicidad, coalesce(evento, ''), dimensiones)
    WHERE vigente;
CREATE INDEX ix_observacion_externa_periodo ON operativo.observacion_externa (variable, periodo_inicio) WHERE vigente;

-- -----------------------------------------------------------------------------
-- Fuentes con extractor automático y las variables que publican
-- -----------------------------------------------------------------------------
INSERT INTO operativo.fuente_datos (codigo, nombre, entidad_propietaria, formato, periodicidad, datos_personales,
    sla_dias, prioritaria, tipo_fuente, condiciones_licencia, cobertura_geografica, variables_principales, observaciones)
VALUES ('sri_ventas', 'Ventas por cantón y actividad (datos abiertos)', 'Servicio de Rentas Internas (SRI)',
    'csv', 'mensual', 'no', 75, true, 'oficial', 'Datos abiertos del SRI; robots.txt permite el acceso',
    'Cantón Cuenca', 'Total de ventas de la sección CIIU I (alojamiento y comidas)',
    'Extracción automática por scraping de https://www.sri.gob.ec/datasets')
ON CONFLICT (codigo) DO NOTHING;

INSERT INTO operativo.variable_externa (codigo, nombre, unidad, descripcion, fuente_id, indicadores)
SELECT 'sri_ventas_seccion_i', 'Ventas de alojamiento y servicios de comidas', 'USD',
       'Total de ventas declaradas de la sección CIIU I en el cantón Cuenca (incluye I55 e I56)', id, ARRAY['D1']
FROM operativo.fuente_datos WHERE codigo = 'sri_ventas'
ON CONFLICT (codigo) DO NOTHING;
