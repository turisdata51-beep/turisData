-- =============================================================================
-- 005: fuentes con extracción automática y su programación
--
-- extractor                 nombre del módulo en backend/app/extractores (null = carga manual)
-- frecuencia_extraccion_dias cada cuántos días se revisa la fuente de forma automática
-- =============================================================================

ALTER TABLE operativo.fuente_datos
    ADD COLUMN IF NOT EXISTS extractor text,
    ADD COLUMN IF NOT EXISTS frecuencia_extraccion_dias integer
        CHECK (frecuencia_extraccion_dias IS NULL OR frecuencia_extraccion_dias > 0);

-- SRI: publica cada mes; se revisa cada semana
UPDATE operativo.fuente_datos SET extractor = 'sri_ventas', frecuencia_extraccion_dias = 7
WHERE codigo = 'sri_ventas';

-- INEC: proyecciones de población (Revisión 2024); cambian muy rara vez
UPDATE operativo.fuente_datos SET
    nombre = 'Proyecciones de población cantonal (Revisión 2024)',
    formato = 'xlsx', periodicidad = 'anual', extractor = 'inec_poblacion', frecuencia_extraccion_dias = 90,
    cobertura_geografica = 'Cantón Cuenca', variables_principales = 'Población total estimada y proyectada 2010–2035',
    condiciones_licencia = 'Datos públicos del INEC; robots.txt permite el acceso',
    observaciones = 'Descarga automática del tabulado XLSX del INEC (hoja 3.2, cantones)'
WHERE codigo = 'inec_poblacion';

INSERT INTO operativo.fuente_datos (codigo, nombre, entidad_propietaria, formato, periodicidad, datos_personales,
    sla_dias, prioritaria, tipo_fuente, condiciones_licencia, cobertura_geografica, variables_principales,
    observaciones, extractor, frecuencia_extraccion_dias)
VALUES
    ('catastro_turistico', 'Catastro turístico nacional', 'Viceministerio de Turismo (MPCEI)',
     'xlsx', 'irregular', 'si', 400, false, 'oficial', 'CC-BY, Portal de Datos Abiertos del Ecuador',
     'Cantón Cuenca y parroquias', 'Establecimientos turísticos por actividad, clasificación y parroquia',
     'API CKAN de datosabiertos.gob.ec. Trae datos personales: solo se guardan conteos agregados',
     'catastro_turistico', 30),
    ('hosteleria_cuenca', 'Hostelería del cantón Cuenca', 'GAD Municipal de Cuenca (Cuenca en Datos)',
     'csv', 'irregular', 'si', 800, false, 'oficial', 'CC No Comercial, portal Cuenca en Datos',
     'Cantón Cuenca', 'Alojamientos con habitaciones y plazas instaladas',
     'API CKAN de cuencaendatos.cuenca.gob.ec. Trae datos personales: solo se guardan totales agregados',
     'hosteleria_cuenca', 30)
ON CONFLICT (codigo) DO NOTHING;

INSERT INTO operativo.variable_externa (codigo, nombre, unidad, descripcion, fuente_id, indicadores)
SELECT v.codigo, v.nombre, v.unidad, v.descripcion, f.id, v.indicadores
FROM (VALUES
    ('inec_poblacion_proyectada', 'Población proyectada', 'personas',
     'Población total del cantón según estimaciones y proyecciones del INEC', 'inec_poblacion', ARRAY['D4', 'D6']),
    ('catastro_establecimientos', 'Establecimientos turísticos registrados', 'establecimientos',
     'Conteo del catastro por actividad (y clasificación en alojamiento)', 'catastro_turistico', ARRAY['B1']),
    ('hosteleria_establecimientos', 'Alojamientos registrados por el municipio', 'establecimientos',
     'Conteo de alojamientos de la base municipal de hostelería', 'hosteleria_cuenca', ARRAY[]::text[]),
    ('hosteleria_habitaciones', 'Habitaciones instaladas', 'habitaciones',
     'Suma de habitaciones declaradas en la base municipal de hostelería', 'hosteleria_cuenca', ARRAY[]::text[]),
    ('hosteleria_plazas', 'Plazas instaladas', 'plazas',
     'Suma de plazas declaradas en la base municipal de hostelería', 'hosteleria_cuenca', ARRAY['D6'])
) AS v (codigo, nombre, unidad, descripcion, fuente, indicadores)
JOIN operativo.fuente_datos f ON f.codigo = v.fuente
ON CONFLICT (codigo) DO NOTHING;
