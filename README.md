# Observatorio Turístico Inteligente de Cuenca

Proyecto de titulación para la Cámara de Turismo del Azuay. Basado en el
*Anteproyecto de titulación* y en el *Manual Metodológico de Indicadores v2*.

> Las cifras que muestra el sistema son **datos de demostración** (26 alojamientos
> ficticios `DEMO-001`…`DEMO-026`, ene-2024 a sep-2026). No representan establecimientos reales.

## Qué incluye

| Parte | Ruta | Contenido |
|---|---|---|
| Sitio público | `/` | Página inicial de la Cámara (textos editables desde el panel) con las cifras del último mes |
| | `/observatorio` | 8 KPI con variación interanual, ocupación año contra año, pernoctaciones por residencia, tabla por parroquia con regla de confidencialidad |
| | `/metodologia` | Fichas de cada indicador (definición, fórmula, unidad, fuentes, limitaciones) |
| Panel admin | `/admin` | Resumen de calidad (Q1–Q5), cargas de archivos, establecimientos, indicadores, usuarios y roles, contenido del sitio, auditoría |
| API | `backend/app` | FastAPI + PostgreSQL: autenticación JWT, roles, importador XLSX/CSV con validación, motor de cálculo de KPI |
| Datos | `db/`, `docs/`, `plantillas/` | Esquema, diccionario de indicadores y plantilla de reporte |

Roles: **administrador** (todo), **analista** (cargas, establecimientos, indicadores),
**consulta** (resumen, indicadores, exportación), **asociado** (sube y ve solo los reportes de su hotel).

## Cómo ejecutarlo

Requisitos: Docker Desktop, Python 3.12+ y Node 20+.

```bash
# 1. Base de datos (crea esquema y datos semilla la primera vez)
docker compose up -d

# 2. Backend
cd backend
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
cp .env.example .env          # y poner JWT_SECRET y contraseñas
.venv/Scripts/python -m app.demo                     # carga los datos de demostración
.venv/Scripts/python -m uvicorn app.main:app --port 8000 --reload

# 3. Frontend (otra terminal)
cd frontend
npm install
npm run dev                   # http://localhost:5173
```

Los usuarios de prueba (administrador, analista, consulta y un asociado) y sus
contraseñas están en `backend/.env`. Ese archivo no debe subirse a git.

Para regenerar los datos demo desde cero: `python -m app.demo --reiniciar`.

## Diseño

Identidad **TurisData** (`frontend/src/index.css`): minimalista sobre fondo blanco, con los
colores de la bandera del Azuay y del logo. El rojo carmín es el único color de interfaz
(botones, navegación, primera serie de los gráficos), el dorado es la segunda serie y la
franja rojo-dorado del pie y del panel es el único adorno. Los indicadores se agrupan en
rejillas unidas por una junta fina en lugar de tarjetas sueltas, y la portada abre con una
frase escrita con las cifras del mes. Tipografías: Poppins (títulos y cifras, la familia
del logo) y Schibsted Grotesk (texto y tablas). Tema único claro.

El logo original está en `frontend/marca/logo-original.png`. Las versiones web (pin, texto,
logo completo en WebP y favicon) se generan con `python scripts/preparar_logo.py`
desde la carpeta `frontend` (requiere Pillow).

## Decisiones pendientes de la Cámara

- Confirmar los 5 KPI del MVP (propuesta: A1, A2, A4, B4, B6; marcados con `mvp_5: true`).
- Mínimo de establecimientos para publicar un agregado (propuesta: 3; `operativo.parametro`).
- Si los hoteles compartirán ingresos de habitaciones (sin eso no hay ADR ni RevPAR).
- Textos reales de la Cámara: dirección, teléfono, correo y sitio web (editar en *Contenido del sitio*).
- Verificar la población cantonal del Censo 2022 (`db/002_sitio.sql`).
