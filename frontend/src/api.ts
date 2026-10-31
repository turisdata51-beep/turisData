// Cliente de la API y formateadores compartidos.

const CLAVE_TOKEN = 'observatorio_token'

export function leerToken(): string | null {
  try { return localStorage.getItem(CLAVE_TOKEN) } catch { return null }
}
export function guardarToken(token: string | null) {
  try {
    if (token) localStorage.setItem(CLAVE_TOKEN, token)
    else localStorage.removeItem(CLAVE_TOKEN)
  } catch { /* almacenamiento no disponible */ }
}

class ErrorApi extends Error {
  estado: number
  constructor(estado: number, mensaje: string) { super(mensaje); this.estado = estado }
}

export async function api<T = unknown>(ruta: string, opciones: RequestInit = {}): Promise<T> {
  const token = leerToken()
  const cabeceras: Record<string, string> = { ...(opciones.headers as Record<string, string>) }
  if (token) cabeceras.Authorization = `Bearer ${token}`
  if (opciones.body && !(opciones.body instanceof FormData)) cabeceras['Content-Type'] = 'application/json'
  const r = await fetch(`/api${ruta}`, { ...opciones, headers: cabeceras })
  if (!r.ok) {
    let mensaje = 'No se pudo completar la acción'
    try {
      const d = await r.json()
      mensaje = typeof d.detail === 'string' ? d.detail : Array.isArray(d.detail) ? d.detail.map((e: { msg: string }) => e.msg).join('. ') : mensaje
    } catch { /* respuesta sin JSON */ }
    if (r.status === 401 && token) guardarToken(null)
    throw new ErrorApi(r.status, mensaje)
  }
  return r.headers.get('content-type')?.includes('json') ? r.json() : (r as unknown as T)
}

export async function descargar(ruta: string, nombre: string) {
  const r = await api<Response>(ruta)
  const url = URL.createObjectURL(await r.blob())
  const a = document.createElement('a')
  a.href = url; a.download = nombre; a.click()
  URL.revokeObjectURL(url)
}

const MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
const MESES_CORTOS = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']

export function mes(periodo: string | null | undefined, corto = false): string {
  if (!periodo) return '—'
  const [a, m] = periodo.split('-').map(Number)
  return corto ? `${MESES_CORTOS[m - 1]} ${String(a).slice(2)}` : `${MESES[m - 1]} ${a}`
}

export function fechaHora(valor: string | null | undefined): string {
  if (!valor) return '—'
  return new Date(valor).toLocaleString('es-EC', { dateStyle: 'medium', timeStyle: 'short' })
}

export function numero(valor: number | null | undefined, decimales = 0): string {
  if (valor === null || valor === undefined) return '—'
  return valor.toLocaleString('es-EC', { minimumFractionDigits: decimales, maximumFractionDigits: decimales })
}

/** Formatea según la unidad del diccionario de indicadores. */
export function valorKpi(valor: number | null, unidad: string): string {
  if (valor === null) return '—'
  if (unidad === '%') return `${numero(valor, 1)} %`
  if (unidad.startsWith('USD')) return `$${numero(valor, 2)}`
  if (unidad.startsWith('noches por llegada')) return numero(valor, 2)
  if (unidad.startsWith('noches por 1.000')) return numero(valor, 1)
  return numero(valor)
}

export function unidadCorta(unidad: string): string {
  if (unidad === '%') return ''
  if (unidad.startsWith('USD por habitación vendida')) return 'por habitación vendida'
  if (unidad.startsWith('USD por habitación disponible')) return 'por habitación disponible'
  return unidad
}

export type Rol = 'administrador' | 'analista' | 'consulta' | 'asociado'
export interface Usuario {
  id: number; correo: string; nombre: string; rol: Rol
  establecimiento_id: number | null; codigo_camara: string | null; nombre_comercial: string | null
}

export interface Kpi {
  codigo: string; nombre: string; unidad: string; definicion: string
  valor: number | null; valor_anio_anterior: number | null; variacion_interanual: number | null
  bandera: string | null; n_unidades: number | null; cobertura_pct: number | null
}
export interface Resumen { periodo: string | null; kpis: Kpi[]; ultima_actualizacion: string | null }

export interface Contenido {
  hero_titulo: string; hero_subtitulo: string; camara_nombre: string; camara_descripcion: string
  mision: string; vision: string; servicios: { titulo: string; texto: string }[]
  destino_titulo: string; destino_texto: string
  contacto_direccion: string; contacto_telefono: string; contacto_correo: string; contacto_web: string
  aviso_datos: string
}
