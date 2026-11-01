-- =============================================================================
-- 001: esquema base - TurisData, Observatorio Turístico de Cuenca
-- PostgreSQL 16 o superior.
--
-- Esquemas (Figura 1 del anteproyecto):
--   operativo : usuarios, fuentes, cargas, establecimientos, reportes, auditoría
--   analitico : indicadores versionados y observaciones calculadas
--
-- Los scripts de esta carpeta se ejecutan en orden numérico al crear la base.
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS operativo;
CREATE SCHEMA IF NOT EXISTS analitico;

-- -----------------------------------------------------------------------------
-- Seguridad: usuarios y roles (RF-01)
-- -----------------------------------------------------------------------------
CREATE TABLE operativo.rol (
    codigo       text PRIMARY KEY,
    descripcion  text NOT NULL
);

INSERT INTO operativo.rol (codigo, descripcion) VALUES
    ('administrador', 'Gestiona usuarios, fuentes, indicadores y configuración'),
    ('analista',      'Carga datos, corrige errores y consulta todos los tableros'),
    ('consulta',      'Solo consulta tableros y exporta datos agregados'),
    ('asociado',      'Establecimiento: sube y ve únicamente sus propios reportes');

CREATE TABLE operativo.geografia (
    id        serial PRIMARY KEY,
    nivel     text NOT NULL CHECK (nivel IN ('canton', 'zona', 'parroquia')),
    nombre    text NOT NULL,
    tipo      text CHECK (tipo IN ('urbana', 'rural')),          -- solo parroquias
    padre_id  integer REFERENCES operativo.geografia (id),
    UNIQUE (nivel, nombre)
);

CREATE TABLE operativo.establecimiento (
    id                serial PRIMARY KEY,
    codigo_camara     text NOT NULL UNIQUE,      -- no se guarda RUC ni cédula (minimización, LOPDP)
    nombre_comercial  text NOT NULL,
    tipo_alojamiento  text NOT NULL,
    categoria         text NOT NULL,
    parroquia_id      integer NOT NULL REFERENCES operativo.geografia (id),
    participa_desde   date NOT NULL,
    participa_hasta   date,                      -- null = sigue participando
    CHECK (participa_hasta IS NULL OR participa_hasta >= participa_desde)
);

CREATE TABLE operativo.usuario (
    id                 serial PRIMARY KEY,
    correo             text NOT NULL UNIQUE,
    nombre             text NOT NULL,
    hash_contrasena    text NOT NULL,            -- argon2/bcrypt, nunca texto plano (RNF-03)
    rol                text NOT NULL REFERENCES operativo.rol (codigo),
    establecimiento_id integer REFERENCES operativo.establecimiento (id),
    activo             boolean NOT NULL DEFAULT true,
    creado_en          timestamptz NOT NULL DEFAULT now(),
    ultimo_acceso      timestamptz,
    -- un asociado siempre está ligado a su establecimiento; los demás roles no
    CHECK ((rol = 'asociado') = (establecimiento_id IS NOT NULL))
);

-- -----------------------------------------------------------------------------
-- Catálogo de fuentes (RF-02; Anexo A del anteproyecto)
-- -----------------------------------------------------------------------------
CREATE TABLE operativo.fuente_datos (
    id                    serial PRIMARY KEY,
    codigo                text NOT NULL UNIQUE,  -- ej. plantilla_alojamiento_camara, inec_poblacion
    nombre                text NOT NULL,
    entidad_propietaria   text NOT NULL,
    responsable_contacto  text,
    finalidad_uso         text,
    formato               text NOT NULL CHECK (formato IN ('api', 'csv', 'xlsx', 'formulario', 'otro')),
    periodicidad          text NOT NULL,
    cobertura_temporal    text,
    cobertura_geografica  text,
    variables_principales text,
    datos_personales      text NOT NULL DEFAULT 'por_determinar'
                          CHECK (datos_personales IN ('si', 'no', 'por_determinar')),
    condiciones_licencia  text,
    reglas_calidad        text,
    sla_dias              integer CHECK (sla_dias > 0),   -- plazo máximo entre actualizaciones (Q3, Q4)
    prioritaria           boolean NOT NULL DEFAULT false,
    tipo_fuente           text NOT NULL CHECK (tipo_fuente IN ('oficial', 'primaria_local', 'comercial', 'sistema')),
    observaciones         text,
    activa                boolean NOT NULL DEFAULT true
);

-- -----------------------------------------------------------------------------
-- Cargas y errores (RF-03, RF-05, RF-09)
-- -----------------------------------------------------------------------------
CREATE TABLE operativo.carga_datos (
    id                   bigserial PRIMARY KEY,
    fuente_id            integer NOT NULL REFERENCES operativo.fuente_datos (id),
    usuario_id           integer REFERENCES operativo.usuario (id),    -- null si la hizo un proceso automático
    mecanismo            text NOT NULL CHECK (mecanismo IN ('archivo', 'api', 'formulario')),
    nombre_archivo       text,
    hash_sha256          text,                   -- detecta re-envíos idénticos
    version_plantilla    text,
    fecha_captura        timestamptz,            -- cuándo se generó el dato en origen
    recibido_en          timestamptz NOT NULL DEFAULT now(),
    registros_recibidos  integer NOT NULL DEFAULT 0,
    registros_validos    integer NOT NULL DEFAULT 0,
    registros_rechazados integer NOT NULL DEFAULT 0,
    campos_criticos_esperados integer NOT NULL DEFAULT 0,
    campos_criticos_validos   integer NOT NULL DEFAULT 0,
    estado               text NOT NULL DEFAULT 'recibida'
                         CHECK (estado IN ('recibida', 'validada', 'con_errores', 'rechazada', 'publicada', 'revertida')),
    CHECK (registros_validos + registros_rechazados <= registros_recibidos),
    CHECK (campos_criticos_validos <= campos_criticos_esperados)
);

CREATE TABLE operativo.carga_error (
    id           bigserial PRIMARY KEY,
    carga_id     bigint NOT NULL REFERENCES operativo.carga_datos (id) ON DELETE CASCADE,
    fila         integer,
    campo        text,
    valor        text,
    regla        text NOT NULL,
    mensaje      text NOT NULL,
    severidad    text NOT NULL CHECK (severidad IN ('error', 'advertencia')),
    corregido_en timestamptz,
    corregido_por integer REFERENCES operativo.usuario (id)
);

-- -----------------------------------------------------------------------------
-- Reporte mensual de alojamiento (una fila validada de la plantilla v1)
-- Un reenvío NO borra el anterior: lo marca como no vigente (trazabilidad, RF-09).
-- -----------------------------------------------------------------------------
CREATE TABLE operativo.reporte_alojamiento_mensual (
    id                              bigserial PRIMARY KEY,
    carga_id                        bigint NOT NULL REFERENCES operativo.carga_datos (id),
    establecimiento_id              integer NOT NULL REFERENCES operativo.establecimiento (id),
    periodo                         date NOT NULL CHECK (extract(day FROM periodo) = 1), -- primer día del mes
    vigente                         boolean NOT NULL DEFAULT true,
    habitaciones_instaladas         integer NOT NULL CHECK (habitaciones_instaladas > 0),
    plazas_instaladas               integer NOT NULL CHECK (plazas_instaladas > 0),
    dias_operacion                  integer NOT NULL,
    habitaciones_noche_disponibles  integer NOT NULL CHECK (habitaciones_noche_disponibles >= 0),
    habitaciones_noche_ocupadas     integer NOT NULL CHECK (habitaciones_noche_ocupadas >= 0),
    plazas_cama_noche_disponibles   integer NOT NULL CHECK (plazas_cama_noche_disponibles >= 0),
    llegadas_residentes             integer NOT NULL CHECK (llegadas_residentes >= 0),
    llegadas_no_residentes          integer NOT NULL CHECK (llegadas_no_residentes >= 0),
    noches_residentes               integer NOT NULL CHECK (noches_residentes >= 0),
    noches_no_residentes            integer NOT NULL CHECK (noches_no_residentes >= 0),
    ingreso_habitaciones_usd        numeric(14, 2) CHECK (ingreso_habitaciones_usd >= 0),  -- opcional
    observaciones                   text,
    -- reglas de consistencia de la plantilla (las mismas que ve el usuario en Excel)
    CONSTRAINT dias_en_rango CHECK (
        dias_operacion BETWEEN 0 AND extract(day FROM (periodo + interval '1 month - 1 day'))),
    CONSTRAINT ocupadas_le_disponibles CHECK (habitaciones_noche_ocupadas <= habitaciones_noche_disponibles),
    CONSTRAINT disponibles_le_capacidad CHECK (
        habitaciones_noche_disponibles <= habitaciones_instaladas * extract(day FROM (periodo + interval '1 month - 1 day'))),
    CONSTRAINT plazas_le_capacidad CHECK (
        plazas_cama_noche_disponibles <= plazas_instaladas * extract(day FROM (periodo + interval '1 month - 1 day'))),
    CONSTRAINT plazas_ge_habitaciones CHECK (plazas_cama_noche_disponibles >= habitaciones_noche_disponibles),
    CONSTRAINT noches_le_plazas CHECK (
        noches_residentes + noches_no_residentes <= plazas_cama_noche_disponibles),
    CONSTRAINT ocupacion_con_noches CHECK (
        (habitaciones_noche_ocupadas = 0) = (noches_residentes + noches_no_residentes = 0))
);

-- un solo reporte vigente por establecimiento y mes
CREATE UNIQUE INDEX ux_reporte_vigente
    ON operativo.reporte_alojamiento_mensual (establecimiento_id, periodo) WHERE vigente;
CREATE INDEX ix_reporte_periodo ON operativo.reporte_alojamiento_mensual (periodo) WHERE vigente;

-- -----------------------------------------------------------------------------
-- Población residente (INEC) para D4 y futuros D5/D6
-- -----------------------------------------------------------------------------
CREATE TABLE operativo.poblacion (
    geografia_id integer NOT NULL REFERENCES operativo.geografia (id),
    anio         integer NOT NULL,
    habitantes   integer NOT NULL CHECK (habitantes > 0),
    tipo         text NOT NULL CHECK (tipo IN ('censo', 'proyeccion', 'estimacion')),
    fuente_id    integer NOT NULL REFERENCES operativo.fuente_datos (id),
    PRIMARY KEY (geografia_id, anio)
);

-- -----------------------------------------------------------------------------
-- Parámetros configurables (sin tocar código)
-- -----------------------------------------------------------------------------
CREATE TABLE operativo.parametro (
    clave       text PRIMARY KEY,
    valor       text NOT NULL,
    descripcion text NOT NULL
);

INSERT INTO operativo.parametro (clave, valor, descripcion) VALUES
    ('min_establecimientos_publicacion', '3',
     'Mínimo de establecimientos en un agregado para poder publicarlo (confidencialidad). PROPUESTA, confirmar con la Cámara.'),
    ('meta_fuentes_al_dia_pct', '80', 'Meta piloto de Q4 (anteproyecto, sección 17).'),
    ('meta_registros_validos_pct', '95', 'Meta piloto de Q5 (anteproyecto, sección 17).');

-- -----------------------------------------------------------------------------
-- Auditoría (RF-10)
-- -----------------------------------------------------------------------------
CREATE TABLE operativo.auditoria (
    id          bigserial PRIMARY KEY,
    ocurrido_en timestamptz NOT NULL DEFAULT now(),
    usuario_id  integer REFERENCES operativo.usuario (id),
    accion      text NOT NULL,        -- login, carga, correccion, exportacion, cambio_config, ...
    entidad     text,
    entidad_id  text,
    resultado   text NOT NULL CHECK (resultado IN ('ok', 'error', 'denegado')),
    detalle     jsonb
);
CREATE INDEX ix_auditoria_fecha ON operativo.auditoria (ocurrido_en);

-- =============================================================================
-- Esquema analítico
-- =============================================================================

-- Indicador versionado: la ficha completa vive en ficha (jsonb) tal como sale de
-- backend/recursos/diccionario_indicadores.yaml. Nunca se modifica una versión publicada (RF-12).
CREATE TABLE analitico.indicador (
    codigo         text NOT NULL,
    version        integer NOT NULL CHECK (version > 0),
    nombre         text NOT NULL,
    tipo_base      text NOT NULL CHECK (tipo_base IN ('estandar', 'kpi_sectorial', 'calculo_operativo', 'interno')),
    unidad         text NOT NULL,
    universo       text NOT NULL,
    ficha          jsonb NOT NULL,
    vigente_desde  date NOT NULL,
    vigente_hasta  date,
    PRIMARY KEY (codigo, version)
);
CREATE UNIQUE INDEX ux_indicador_vigente ON analitico.indicador (codigo) WHERE vigente_hasta IS NULL;

-- Valor calculado de un indicador (entidad ObservacionTuristica del anteproyecto,
-- ampliada con los campos que exige el manual).
CREATE TABLE analitico.observacion (
    id                  bigserial PRIMARY KEY,
    indicador_codigo    text NOT NULL,
    indicador_version   integer NOT NULL,
    periodo_inicio      date NOT NULL,
    periodo_fin         date NOT NULL,
    periodicidad        text NOT NULL,
    geografia_id        integer NOT NULL REFERENCES operativo.geografia (id),
    dimensiones         jsonb NOT NULL DEFAULT '{}'::jsonb,   -- ej. {"residencia":"no_residente","categoria":"4 estrellas"}
    valor               numeric,                              -- null = no calculable
    motivo_no_calculable text,
    numerador           numeric,
    denominador         numeric,
    bandera             text NOT NULL CHECK (bandera IN ('observado', 'estimado', 'pronosticado')),
    n_unidades          integer,                              -- establecimientos que aportan al valor
    cobertura_pct       numeric(5, 2),                        -- Q1 asociada al valor
    publicable          boolean NOT NULL,                     -- false si n_unidades < mínimo de confidencialidad
    fuente_ids          integer[] NOT NULL,
    carga_ids           bigint[],
    calculado_en        timestamptz NOT NULL DEFAULT now(),
    FOREIGN KEY (indicador_codigo, indicador_version) REFERENCES analitico.indicador (codigo, version),
    CHECK (periodo_fin >= periodo_inicio),
    CHECK ((valor IS NULL) = (motivo_no_calculable IS NOT NULL))
);

-- Un valor por indicador/período/geografía/combinación de dimensiones;
-- un recálculo reemplaza la fila (upsert).
CREATE UNIQUE INDEX ux_observacion
    ON analitico.observacion (indicador_codigo, indicador_version, periodo_inicio, periodicidad, geografia_id, dimensiones);

-- -----------------------------------------------------------------------------
-- Vista base para el motor de cálculo: agregados mensuales por cantón y
-- parroquia a partir de los reportes vigentes. Los KPI (A1, A2, A4, B4, B6...)
-- se calculan sobre estas sumas, nunca promediando porcentajes por hotel.
-- -----------------------------------------------------------------------------
CREATE VIEW analitico.v_alojamiento_mensual AS
SELECT r.periodo,
       g.nivel,
       g.id                                        AS geografia_id,
       g.nombre                                    AS geografia,
       count(*)                                    AS establecimientos_reportantes,
       count(r.ingreso_habitaciones_usd)           AS establecimientos_con_ingreso,
       sum(r.llegadas_residentes + r.llegadas_no_residentes)          AS llegadas_total,
       sum(r.noches_residentes + r.noches_no_residentes)              AS noches_total,
       sum(r.noches_no_residentes)                                    AS noches_no_residentes,
       sum(r.habitaciones_noche_disponibles)                          AS habitaciones_noche_disponibles,
       sum(r.habitaciones_noche_ocupadas)                             AS habitaciones_noche_ocupadas,
       sum(r.plazas_cama_noche_disponibles)                           AS plazas_cama_noche_disponibles,
       sum(r.ingreso_habitaciones_usd)                                AS ingreso_habitaciones_usd,
       -- ocupadas y disponibles solo de quienes reportan ingreso, para que ADR y RevPAR
       -- usen el mismo subconjunto en numerador y denominador
       sum(r.habitaciones_noche_ocupadas)    FILTER (WHERE r.ingreso_habitaciones_usd IS NOT NULL) AS hn_ocupadas_con_ingreso,
       sum(r.habitaciones_noche_disponibles) FILTER (WHERE r.ingreso_habitaciones_usd IS NOT NULL) AS hn_disponibles_con_ingreso,
       sum(r.llegadas_no_residentes)                                  AS llegadas_no_residentes
FROM operativo.reporte_alojamiento_mensual r
JOIN operativo.establecimiento e ON e.id = r.establecimiento_id
JOIN operativo.geografia p       ON p.id = e.parroquia_id
JOIN operativo.geografia g       ON g.id = p.id OR g.id = p.padre_id
WHERE r.vigente
GROUP BY r.periodo, g.nivel, g.id, g.nombre;
