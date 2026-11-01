# TurisData – Observatorio Turístico de Cuenca

Proyecto de titulación para la Cámara de Turismo del Azuay. Basado en el
*Anteproyecto de titulación* y en el *Manual Metodológico de Indicadores v2*.

> Las cifras que muestra el sistema son **datos de demostración** (26 alojamientos
> ficticios `DEMO-001`…`DEMO-026`, ene-2024 a sep-2026). No representan establecimientos reales.
> Las ventas del SRI sí son datos reales obtenidos por scraping.

## Qué incluye

| Parte | Ruta | Contenido |
|---|---|---|
| Sitio público | `/` | Página inicial de la Cámara (textos editables desde el panel) con las cifras del último mes |
| | `/observatorio` | 8 KPI con variación interanual, ocupación año contra año, pernoctaciones por residencia, tabla por parroquia con regla de confidencialidad |
| | `/metodologia` | Fichas de cada indicador (definición, fórmula, unidad, fuentes, limitaciones) |
| Panel admin | `/admin` | Resumen de calidad (Q1–Q5), cargas de archivos, establecimientos, indicadores, usuarios y roles, contenido del sitio, auditoría |

Roles: **administrador** (todo), **analista** (cargas, establecimientos, indicadores),
**consulta** (resumen, indicadores, exportación), **asociado** (sube y ve solo los reportes de su hotel).

## Estructura

```
backend/
  app/
    main.py          arma la aplicación FastAPI y registra las rutas
    nucleo/          configuración, conexión a la base y seguridad (contraseñas, JWT, roles)
    api/             rutas HTTP: publico, auth y admin/ (una por sección del panel)
    servicios/       lógica de negocio: cálculo de indicadores, carga de reportes, diccionario
    extractores/     scraping y descargas automáticas (base común + un módulo por fuente)
    scripts/         tareas de terminal: datos de demostración y generación de la plantilla
  recursos/          archivos que lee el sistema: diccionario de indicadores y plantillas
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
| `python -m app.scripts.generar_plantilla` | Regenera la plantilla Excel/CSV del reporte mensual |

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
