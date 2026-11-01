import { useEffect, useState } from 'react'
import { useLocation } from 'react-router-dom'

/** Estado de un menú desplegable de móvil: se cierra al cambiar de página o con Escape. */
export function useMenuMovil() {
  const [abierto, setAbierto] = useState(false)
  const { pathname } = useLocation()
  // Al cambiar de página se cierra (ajuste durante el render, sin efecto extra)
  const [rutaAnterior, setRutaAnterior] = useState(pathname)
  if (rutaAnterior !== pathname) {
    setRutaAnterior(pathname)
    setAbierto(false)
  }
  useEffect(() => {
    if (!abierto) return
    const alPresionar = (e: KeyboardEvent) => { if (e.key === 'Escape') setAbierto(false) }
    window.addEventListener('keydown', alPresionar)
    return () => window.removeEventListener('keydown', alPresionar)
  }, [abierto])
  return { abierto, alternar: () => setAbierto(a => !a) }
}
