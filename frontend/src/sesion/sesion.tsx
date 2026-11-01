import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react'
import { api, guardarToken, leerToken } from '../lib/api'
import type { Usuario } from '../lib/tipos'

type Sesion = {
  usuario: Usuario | null
  cargando: boolean
  entrar: (correo: string, contrasena: string) => Promise<void>
  salir: () => void
}

const Contexto = createContext<Sesion | null>(null)

export function ProveedorSesion({ children }: { children: ReactNode }) {
  const [usuario, setUsuario] = useState<Usuario | null>(null)
  const [cargando, setCargando] = useState(Boolean(leerToken()))

  useEffect(() => {
    if (!leerToken()) return
    api<Usuario>('/auth/yo').then(setUsuario).catch(() => guardarToken(null)).finally(() => setCargando(false))
  }, [])

  const entrar = useCallback(async (correo: string, contrasena: string) => {
    const { token } = await api<{ token: string }>('/auth/login', { method: 'POST', body: JSON.stringify({ correo, contrasena }) })
    guardarToken(token)
    setUsuario(await api<Usuario>('/auth/yo'))
  }, [])

  const salir = useCallback(() => { guardarToken(null); setUsuario(null) }, [])

  return <Contexto.Provider value={{ usuario, cargando, entrar, salir }}>{children}</Contexto.Provider>
}

export function useSesion() {
  const s = useContext(Contexto)
  if (!s) throw new Error('useSesion fuera de ProveedorSesion')
  return s
}
