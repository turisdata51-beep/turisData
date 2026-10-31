-- Datos semilla: cantón Cuenca y sus 36 parroquias (15 urbanas, 21 rurales).
INSERT INTO operativo.geografia (nivel, nombre) VALUES ('canton', 'Cuenca');

INSERT INTO operativo.geografia (nivel, nombre, tipo, padre_id) VALUES
    ('parroquia', 'Bellavista', 'urbana', (SELECT id FROM operativo.geografia WHERE nivel = 'canton' AND nombre = 'Cuenca')),
    ('parroquia', 'Cañaribamba', 'urbana', (SELECT id FROM operativo.geografia WHERE nivel = 'canton' AND nombre = 'Cuenca')),
    ('parroquia', 'El Batán', 'urbana', (SELECT id FROM operativo.geografia WHERE nivel = 'canton' AND nombre = 'Cuenca')),
    ('parroquia', 'El Sagrario', 'urbana', (SELECT id FROM operativo.geografia WHERE nivel = 'canton' AND nombre = 'Cuenca')),
    ('parroquia', 'El Vecino', 'urbana', (SELECT id FROM operativo.geografia WHERE nivel = 'canton' AND nombre = 'Cuenca')),
    ('parroquia', 'Gil Ramírez Dávalos', 'urbana', (SELECT id FROM operativo.geografia WHERE nivel = 'canton' AND nombre = 'Cuenca')),
    ('parroquia', 'Hermano Miguel', 'urbana', (SELECT id FROM operativo.geografia WHERE nivel = 'canton' AND nombre = 'Cuenca')),
    ('parroquia', 'Huayna Cápac', 'urbana', (SELECT id FROM operativo.geografia WHERE nivel = 'canton' AND nombre = 'Cuenca')),
    ('parroquia', 'Machángara', 'urbana', (SELECT id FROM operativo.geografia WHERE nivel = 'canton' AND nombre = 'Cuenca')),
    ('parroquia', 'Monay', 'urbana', (SELECT id FROM operativo.geografia WHERE nivel = 'canton' AND nombre = 'Cuenca')),
    ('parroquia', 'San Blas', 'urbana', (SELECT id FROM operativo.geografia WHERE nivel = 'canton' AND nombre = 'Cuenca')),
    ('parroquia', 'San Sebastián', 'urbana', (SELECT id FROM operativo.geografia WHERE nivel = 'canton' AND nombre = 'Cuenca')),
    ('parroquia', 'Sucre', 'urbana', (SELECT id FROM operativo.geografia WHERE nivel = 'canton' AND nombre = 'Cuenca')),
    ('parroquia', 'Totoracocha', 'urbana', (SELECT id FROM operativo.geografia WHERE nivel = 'canton' AND nombre = 'Cuenca')),
    ('parroquia', 'Yanuncay', 'urbana', (SELECT id FROM operativo.geografia WHERE nivel = 'canton' AND nombre = 'Cuenca'));

INSERT INTO operativo.geografia (nivel, nombre, tipo, padre_id) VALUES
    ('parroquia', 'Baños', 'rural', (SELECT id FROM operativo.geografia WHERE nivel = 'canton' AND nombre = 'Cuenca')),
    ('parroquia', 'Chaucha', 'rural', (SELECT id FROM operativo.geografia WHERE nivel = 'canton' AND nombre = 'Cuenca')),
    ('parroquia', 'Checa', 'rural', (SELECT id FROM operativo.geografia WHERE nivel = 'canton' AND nombre = 'Cuenca')),
    ('parroquia', 'Chiquintad', 'rural', (SELECT id FROM operativo.geografia WHERE nivel = 'canton' AND nombre = 'Cuenca')),
    ('parroquia', 'Cumbe', 'rural', (SELECT id FROM operativo.geografia WHERE nivel = 'canton' AND nombre = 'Cuenca')),
    ('parroquia', 'El Valle', 'rural', (SELECT id FROM operativo.geografia WHERE nivel = 'canton' AND nombre = 'Cuenca')),
    ('parroquia', 'Llacao', 'rural', (SELECT id FROM operativo.geografia WHERE nivel = 'canton' AND nombre = 'Cuenca')),
    ('parroquia', 'Molleturo', 'rural', (SELECT id FROM operativo.geografia WHERE nivel = 'canton' AND nombre = 'Cuenca')),
    ('parroquia', 'Nulti', 'rural', (SELECT id FROM operativo.geografia WHERE nivel = 'canton' AND nombre = 'Cuenca')),
    ('parroquia', 'Octavio Cordero Palacios', 'rural', (SELECT id FROM operativo.geografia WHERE nivel = 'canton' AND nombre = 'Cuenca')),
    ('parroquia', 'Paccha', 'rural', (SELECT id FROM operativo.geografia WHERE nivel = 'canton' AND nombre = 'Cuenca')),
    ('parroquia', 'Quingeo', 'rural', (SELECT id FROM operativo.geografia WHERE nivel = 'canton' AND nombre = 'Cuenca')),
    ('parroquia', 'Ricaurte', 'rural', (SELECT id FROM operativo.geografia WHERE nivel = 'canton' AND nombre = 'Cuenca')),
    ('parroquia', 'San Joaquín', 'rural', (SELECT id FROM operativo.geografia WHERE nivel = 'canton' AND nombre = 'Cuenca')),
    ('parroquia', 'Santa Ana', 'rural', (SELECT id FROM operativo.geografia WHERE nivel = 'canton' AND nombre = 'Cuenca')),
    ('parroquia', 'Sayausí', 'rural', (SELECT id FROM operativo.geografia WHERE nivel = 'canton' AND nombre = 'Cuenca')),
    ('parroquia', 'Sidcay', 'rural', (SELECT id FROM operativo.geografia WHERE nivel = 'canton' AND nombre = 'Cuenca')),
    ('parroquia', 'Sinincay', 'rural', (SELECT id FROM operativo.geografia WHERE nivel = 'canton' AND nombre = 'Cuenca')),
    ('parroquia', 'Tarqui', 'rural', (SELECT id FROM operativo.geografia WHERE nivel = 'canton' AND nombre = 'Cuenca')),
    ('parroquia', 'Turi', 'rural', (SELECT id FROM operativo.geografia WHERE nivel = 'canton' AND nombre = 'Cuenca')),
    ('parroquia', 'Victoria del Portete', 'rural', (SELECT id FROM operativo.geografia WHERE nivel = 'canton' AND nombre = 'Cuenca'));

INSERT INTO operativo.fuente_datos
    (codigo, nombre, entidad_propietaria, formato, periodicidad, datos_personales, sla_dias, prioritaria, tipo_fuente) VALUES
    ('plantilla_alojamiento_camara', 'Reporte mensual de alojamiento (plantilla v1)', 'Cámara de Turismo del Azuay / asociados',
     'xlsx', 'mensual', 'no', 45, true, 'primaria_local'),
    ('inec_poblacion', 'Población cantonal (Censo 2022 y proyecciones)', 'INEC', 'csv', 'anual', 'no', 400, false, 'oficial'),
    ('sistema', 'Registros internos del observatorio', 'Observatorio', 'otro', 'diaria', 'no', NULL, false, 'sistema');
