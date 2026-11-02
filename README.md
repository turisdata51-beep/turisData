# TurisData – Observatorio Turístico de Cuenca

Proyecto de titulación para la Cámara de Turismo del Azuay. Basado en el
*Anteproyecto de titulación* y en el *Manual Metodológico de Indicadores v2*.

> Las cifras que muestra el sistema son **datos de demostración** (26 alojamientos
> ficticios `DEMO-001`…`DEMO-026`, ene-2024 a sep-2026). No representan establecimientos reales.
> Son datos reales, obtenidos por scraping: ventas del SRI, catastro turístico, hostelería municipal y población del INEC.

## Qué incluye

| Parte | Ruta | Contenido |
|---|---|---|
| Sitio público | `/` | Página inicial de la Cámara (textos editables desde el panel) con las cifras del último mes |
| | `/observatorio` | 8 KPI con variación interanual, ocupación año contra año, pernoctaciones por residencia y tabla por parroquia. Filtros por mes, zona (cantón o parroquia), categoría y rango de fechas, guardados en la dirección web para compartirlos |
| | `/economia` | Ventas de alojamiento y comidas del SRI desde 2018 (mensual, anual, acumulado del año) y oferta registrada: alojamientos por tipo y parroquia, capacidad instalada y plazas por 100 habitantes |
| | `/sostenibilidad` | Empleo estacional (D3), habitaciones accesibles (E1), establecimientos certificados (E6) y agua, energía y residuos por noche turística (E3–E5), con lo que reportan los asociados en las plantillas |
| | `/metodologia` | Fichas de cada indicador (definición, fórmula, unidad, fuentes, limitaciones) |
| Panel admin | `/admin` | Resumen de calidad (Q1–Q5), cargas de archivos, fuentes y extracciones automáticas, establecimientos, indicadores, usuarios y roles, contenido del sitio, auditoría |

Roles: **administrador** (todo), **analista** (cargas, establecimientos, indicadores),
**consulta** (resumen, indicadores, exportación), **asociado** (sube y ve solo los reportes de su hotel).

## Estructura

```
backend/
  app/
    main.py          arma la aplicación FastAPI y registra las rutas
    nucleo/          configuración, conexión a la base y seguridad (contraseñas, JWT, roles)
    api/             rutas HTTP: publico, auth y admin/ (una por sección del panel)
    servicios/       lógica de negocio: cálculo de indicadores, diccionario, programador de
                     extracciones y plantillas/ (una clase por plantilla de carga)
    extractores/     scraping y descargas (base común, apoyo CKAN y un módulo por fuente)
    scripts/         tareas de terminal: datos de demostración
  recursos/          archivos que lee el sistema: diccionario de indicadores
db/                  scripts SQL numerados; se ejecutan en orden al crear la base
frontend/
  src/
    main.tsx         rutas de la aplicación
    lib/             cliente de la API, formatos, tipos y hooks
    componentes/     piezas reutilizables (marca, encabezado, pie, indicador…)
    sesion/          inicio de sesión y usuario actual
    paginas/publico/ sitio público
    paginas/admin/   panel de administración
  public/            logo e imágenes servidas por la web
docs/                documentación: modelo de datos, matriz de fuentes, pendientes, logo original
```

## Cómo ejecutarlo

Requisitos: Docker Desktop, Python 3.12+ y Node 20+.

```bash
# 1. Base de datos (la primera vez ejecuta los scripts de db/)
docker compose up -d

# 2. Backend
cd backend
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
cp .env.example .env          # y poner JWT_SECRET y contraseñas
.venv/Scripts/python -m app.scripts.datos_demo       # carga los datos de demostración
.venv/Scripts/python -m uvicorn app.main:app --port 8000 --reload

# 3. Frontend (otra terminal)
cd frontend
npm install
npm run dev                   # http://localhost:5173
```

Los usuarios de prueba (administrador, analista, consulta y un asociado) y sus
contraseñas están en `backend/.env`. Ese archivo no debe subirse a git.

### Tareas de terminal (carpeta `backend`)

| Comando | Qué hace |
|---|---|
| `python -m app.scripts.datos_demo --reiniciar` | Borra y vuelve a crear los datos de demostración |
| `python -m app.extractores` | Lista los extractores disponibles |
| `python -m app.extractores sri_ventas` | Ejecuta un extractor (`--todos` para todos, `--forzar` aunque la fuente no haya cambiado) |

### Extracción automática

| Extractor | Fuente | Qué guarda | Frecuencia |
|---|---|---|---|
| `sri_ventas` | SRI, datos abiertos | Ventas mensuales de alojamiento y comidas en Cuenca | cada 7 días |
| `catastro_turistico` | Catastro turístico nacional (datosabiertos.gob.ec) | Establecimientos por parroquia, actividad y clasificación | cada 30 días |
| `hosteleria_cuenca` | Hostelería municipal (Cuenca en Datos) | Alojamientos, habitaciones y plazas instaladas | cada 30 días |
| `inec_poblacion` | INEC, proyecciones Revisión 2024 | Población de Cuenca 2010–2035 | cada 90 días |

La API revisa las fuentes cada 15 minutos y ejecuta las que ya cumplieron su frecuencia,
de una en una. Respeta el `robots.txt` y el `Crawl-Delay` de cada sitio, solo guarda datos
agregados (nunca los datos personales que traen algunos archivos) y recalcula los
indicadores cuando llega algo nuevo. La frecuencia se cambia y la ejecución manual se lanza
desde *Panel → Fuentes y extracciones*. Para desactivarla: `EXTRACCION_AUTOMATICA=0` en `backend/.env`.

### Plantillas de carga

Lo que no se puede obtener de la web se sube desde *Panel → Cargas de datos*. Cada plantilla se
descarga en Excel (con listas desplegables, instrucciones y diccionario) o CSV, siempre
generada al momento con los establecimientos, parroquias y variables actuales de la base.

| Plantilla | Quién la sube | Período | Indicadores que alimenta |
|---|---|---|---|
| Alojamiento mensual | asociado, analista, administrador | mes | ocupación, estancia, llegadas, ingresos (grupos A y B) |
| Empleo | asociado, analista, administrador | trimestre (`2026-T3`) | D3 empleo estacional |
| Accesibilidad y certificaciones | asociado, analista, administrador | año | E1 habitaciones accesibles, E6 certificados |
| Consumos de agua, energía y residuos | asociado, analista, administrador | mes | E3, E4, E5 por noche turística |
| Series de otras entidades | analista, administrador | mes, trimestre, año, feriado o evento | aeropuerto, terminal, Cajas, feriados |

Al subir un archivo el sistema valida fila por fila, guarda solo las filas válidas, muestra
los errores con su fila y columna, y recalcula los indicadores. Un reenvío del mismo período
reemplaza el dato anterior, que queda en el historial. Para agregar una plantilla nueva basta
una clase en `backend/app/servicios/plantillas/` registrada en `PLANTILLAS`.

## Pruebas

```bash
# Backend (carpeta backend; requiere la base de docker compose levantada)
.venv/Scripts/python -m pip install -r requirements-dev.txt
.venv/Scripts/python -m pytest --cov=app

# Frontend (carpeta frontend)
npm test
```

Las pruebas del backend crean su propia base (`observatorio_pruebas`) desde los scripts de
`db/`, así que nunca tocan los datos de desarrollo. Cubren:

| Archivo | Qué verifica |
|---|---|
| `test_unitarias.py` | Normalización de parroquias, fechas en nombres de archivo, contraseñas, lectura de cada formato de las fuentes |
| `test_carga_alojamiento.py` | Validaciones fila por fila, reemplazo con historial, archivo repetido, permisos del hotel asociado |
| `test_plantillas.py` | Empleo, accesibilidad, consumos y series externas: reglas, historial, cálculo de D3, E1, E3–E6 y Excel descargable |
| `test_indicadores.py` | Fórmulas del manual calculadas a mano, confidencialidad, población por año, B1 y D6 desde fuentes externas |
| `test_api.py` | Inicio de sesión, permisos de cada rol, filtros públicos, economía, oferta, sostenibilidad, exportación, auditoría |
| `test_extractores.py` | Historial de versiones, fuente sin cambios, `robots.txt`, bloqueo de ejecuciones dobles, programador |
| `test_descargas.py` | Scraping completo de SRI, catastro, hostelería e INEC contra sitios simulados (sin internet) |
| `frontend/src/lib/formato.test.ts` | Formato de fechas, números y unidades en español |

En GitHub, `.github/workflows/pruebas.yml` ejecuta todo esto (más el análisis estático y la
compilación) en cada push, con un PostgreSQL temporal.

## Diseño

Identidad **TurisData** (`frontend/src/index.css`): minimalista sobre fondo blanco, con los
colores de la bandera del Azuay y del logo. El rojo carmín es el único color de interfaz
(botones, navegación, primera serie de los gráficos), el dorado es la segunda serie y la
franja rojo-dorado del pie y del panel es el único adorno. Los indicadores se agrupan en
rejillas unidas por una junta fina en lugar de tarjetas sueltas, y la portada abre con una
frase escrita con las cifras del mes. Tipografías: Poppins (títulos y cifras, la familia
del logo) y Schibsted Grotesk (texto y tablas). Tema único claro. En móvil, el sitio y el
panel usan menú hamburguesa.

El logo original está en `docs/marca/logo-original.png`; las versiones web están en `frontend/public/`.

## Documentación

- [Modelo de datos (entidad-relación)](docs/modelo_datos.md)
- [Pendientes y responsables](docs/PENDIENTES.md)
- Matriz de indicadores y fuentes: `docs/fuentes/matriz_indicadores_fuentes.xlsx`
