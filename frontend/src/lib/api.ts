// Cliente HTTP de la API: añade el token de sesión y convierte los errores en mensajes legibles.

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
    throw new Error(mensaje)
  }
  return r.headers.get('content-type')?.includes('json') ? r.json() : (r as unknown as T)
}

/** Descarga un archivo protegido por sesión (no sirve un enlace normal porque necesita el token). */
export async function descargar(ruta: string, nombre: string) {
  const r = await api<Response>(ruta)
  const url = URL.createObjectURL(await r.blob())
  const a = document.createElement('a')
  a.href = url; a.download = nombre; a.click()
  URL.revokeObjectURL(url)
}
