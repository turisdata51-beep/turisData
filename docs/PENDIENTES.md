# Pendientes de TurisData

Estado al 1 de noviembre de 2026. Referencias: anteproyecto (RF, RNF, E), manual metodológico y reunión con el profesor.
Marca `[x]` cuando se cumpla.

## 1. Desarrollo del sistema (equipo de desarrollo)

**Datos por scraping y descarga automática**
- [ ] Extractor del catastro turístico (Datos Abiertos Ecuador, API CKAN)
- [ ] Extractor de hostelería con habitaciones y plazas (Cuenca en Datos, API CKAN)
- [ ] Extractor de proyecciones de población (INEC, XLSX)
- [ ] Extractor de empleo por rama para Cuenca (ENEMDU, INEC)
- [ ] Extractor de informes de ocupación en feriados (Fundación Turismo para Cuenca, PDF)
- [ ] Extractor del boletín mensual del MPCEI (contexto provincial, PDF)
- [ ] Ejecución programada de los extractores (RF-04)
- [ ] Pantalla "Fuentes y extracciones" en el panel: estado, errores, botón de ejecutar (RF-02, RF-04)

**Indicadores**
- [ ] Calcular B1–B3 (capacidad instalada) con los datos municipales
- [ ] Calcular D1 con las ventas del SRI (como indicador de actividad)
- [ ] Calcular D2 (empleo) y D6 (plazas por 100 residentes)
- [ ] Usar la población proyectada por año en D4 (hoy usa el censo 2022)

**Dashboards**
- [ ] Filtros por rango de fechas, parroquia, tipo y categoría de alojamiento (RF-07)
- [ ] Página económica con las ventas del SRI y su tendencia
- [ ] Fecha de actualización por indicador (RF-11)
- [ ] Exportación a PDF además de CSV (RF-08)

**Carga de información en el panel**
- [ ] Plantilla de empleo (total y estacional)
- [ ] Plantilla de accesibilidad y certificaciones
- [ ] Plantilla de consumos de agua, energía y residuos
- [ ] Carga manual de series de otras entidades (aeropuerto, terminal, Cajas, feriados)
- [ ] Pantalla para consultar y corregir datos históricos (RF-09)

**Calidad, seguridad y operación**
- [ ] Sacar las cuentas demo del `.env` (solo queda el administrador inicial)
- [ ] Pruebas automáticas: cálculo, validaciones, permisos, API (E5)
- [ ] Revisión de accesibilidad WCAG 2.2 AA (RNF-01)
- [ ] Prueba de rendimiento: consultas típicas en menos de 2 s (RNF-02)
- [ ] Respaldos automáticos y prueba de restauración (RNF-05)
- [ ] Dockerizar API y web (al final) (RNF-07)
- [ ] Despliegue con dominio y HTTPS (E6)
- [ ] Manual técnico, manual de usuario, guía de administración y de recuperación (E7)
- [ ] Machine learning opcional, solo con 12 meses o más de datos reales (fase 5)

## 2. Estudiantes

- [ ] Informar al profesor que el scraping cubre 7 de 43 indicadores (matriz en `docs/fuentes/`)
- [ ] Resolver el permiso de GitHub y subir el repositorio (agregar al compañero como colaborador)
- [ ] Crear las cuentas de despliegue (Neon, Render, Vercel u Oracle Cloud)
- [ ] Diseñar y aplicar encuestas a visitantes y residentes, si entran en el alcance
- [ ] Capacitación a usuarios de la Cámara (E8)
- [ ] Memoria de titulación y defensa (E10)

## 3. Profesor / tutor

- [ ] Designar formalmente al tutor académico
- [ ] Aprobar el inventario de fuentes y requisitos (E1)
- [ ] Aprobar arquitectura, modelo de datos y diccionario (E2)
- [ ] Definir si las encuestas forman parte de la tesis
- [ ] Definir si se descartan los indicadores de alquiler de corta estancia (C1–C6)
- [ ] Definir dónde quedan los dashboards (sitio público o panel)

## 4. Cámara de Turismo del Azuay

- [ ] Designar un enlace con capacidad de decisión
- [ ] Carta o convenio de auspicio (hosting, herramientas, traslados)
- [ ] Padrón de hoteles participantes y acuerdo de confidencialidad
- [ ] Reportes mensuales con la plantilla v1 y, si existe, el histórico
- [ ] Confirmar si los hoteles comparten ingresos (ADR y RevPAR)
- [ ] Confirmar los 5 KPI del MVP (propuesta: A1, A2, A4, B4, B6)
- [ ] Confirmar el mínimo de hoteles para publicar un dato (propuesta: 3) y el plazo de entrega (propuesta: 15 días)
- [ ] Datos de contacto, misión y visión reales para la página de inicio
- [ ] Datos de empleo, accesibilidad y certificaciones de los asociados
- [ ] Usuarios clave para las pruebas de aceptación
- [ ] Quién administrará el sistema tras la graduación
- [ ] Dónde se alojarán los datos reales (hosting definitivo)
- [ ] Apoyo para aplicar encuestas, si se hacen

## 5. Otras entidades (solicitud formal, idealmente vía la Cámara)

- [ ] CORPAC: pasajeros mensuales del aeropuerto Mariscal Lamar
- [ ] Terminal Terrestre: llegadas y salidas mensuales
- [ ] ETAPA EP: visitantes mensuales del Parque Nacional Cajas
- [ ] ETAPA, Centrosur y EMAC: consumos del sector turístico (fase avanzada)
- [ ] Viceministerio de Turismo (MPCEI): Encuesta Coyuntural de Alojamiento para Cuenca
- [ ] AirDNA: licencia académica o de pago, solo si se decide mantener C1–C6
