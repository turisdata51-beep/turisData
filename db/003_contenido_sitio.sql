-- =============================================================================
-- 003: contenido editable del sitio público y población de referencia
-- =============================================================================

-- Textos de la página inicial (landing). Se editan desde el panel admin.
CREATE TABLE operativo.contenido_sitio (
    clave           text PRIMARY KEY,
    valor           jsonb NOT NULL,
    actualizado_en  timestamptz NOT NULL DEFAULT now(),
    actualizado_por integer REFERENCES operativo.usuario (id)
);

INSERT INTO operativo.contenido_sitio (clave, valor) VALUES
('landing', $${
  "hero_titulo": "Observatorio Turístico Inteligente de Cuenca",
  "hero_subtitulo": "Datos confiables y comparables sobre el turismo de Cuenca para que el sector tome mejores decisiones.",
  "camara_nombre": "Cámara de Turismo del Azuay",
  "camara_descripcion": "La Cámara de Turismo del Azuay es el gremio que agrupa a los prestadores de servicios turísticos de la provincia: alojamiento, alimentos y bebidas, agencias de viaje, transporte turístico y actividades recreativas. Representa al sector ante las instituciones públicas y privadas e impulsa el desarrollo de Cuenca y el Azuay como destino.",
  "mision": "Representar, fortalecer y promover a los prestadores de servicios turísticos del Azuay, impulsando un turismo competitivo y sostenible.",
  "vision": "Ser el referente gremial del turismo en el austro ecuatoriano, apoyado en información y cooperación entre sus asociados.",
  "servicios": [
    {"titulo": "Representación gremial", "texto": "Defensa de los intereses del sector ante autoridades locales y nacionales."},
    {"titulo": "Capacitación", "texto": "Formación continua para mejorar la calidad del servicio turístico."},
    {"titulo": "Promoción del destino", "texto": "Participación en ferias, campañas y alianzas para atraer visitantes."},
    {"titulo": "Inteligencia turística", "texto": "Este observatorio: indicadores de demanda y alojamiento para decidir con evidencia."}
  ],
  "destino_titulo": "Cuenca, destino patrimonial",
  "destino_texto": "El Centro Histórico de Santa Ana de los Ríos de Cuenca es Patrimonio Cultural de la Humanidad desde 1999, y en 2025 la UNESCO reconoció a Cuenca como Ciudad Creativa de la Gastronomía.",
  "contacto_direccion": "[Dirección de la Cámara]",
  "contacto_telefono": "[Teléfono]",
  "contacto_correo": "[correo@camara]",
  "contacto_web": "[sitio web oficial]",
  "aviso_datos": "Las cifras actuales son DATOS DE DEMOSTRACIÓN generados para el prototipo; no representan a establecimientos reales."
}$$::jsonb);

-- Población del cantón Cuenca, Censo de Población y Vivienda 2022 (INEC).
-- Verificar la cifra oficial antes de usar el sistema con datos reales.
INSERT INTO operativo.poblacion (geografia_id, anio, habitantes, tipo, fuente_id)
SELECT g.id, 2022, 596101, 'censo', f.id
FROM operativo.geografia g, operativo.fuente_datos f
WHERE g.nivel = 'canton' AND g.nombre = 'Cuenca' AND f.codigo = 'inec_poblacion';
