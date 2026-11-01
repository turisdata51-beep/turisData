import { useEffect, useState } from 'react'
import { api } from '../lib/api'
import type { Contenido } from '../lib/tipos'

/** Pie del sitio público con los datos de contacto editables desde el panel. */
export function PiePublico() {
  const [c, setC] = useState<Contenido | null>(null)
  useEffect(() => { api<Contenido>('/public/contenido').then(setC).catch(() => setC(null)) }, [])
  return (
    <footer className="mt-16 border-t border-linea">
      <div className="marco grid gap-8 py-12 sm:grid-cols-[1.4fr_1fr_1fr]">
        <div className="min-w-0 space-y-3">
          <img src="/marca-texto.png" alt="TurisData" className="h-5 w-auto" width={130} height={20} />
          <p className="max-w-[42ch] text-sm text-piedra">
            Observatorio turístico de Cuenca de la {c?.camara_nombre ?? 'Cámara de Turismo del Azuay'}. Publica datos agregados y anónimos de los alojamientos participantes.
          </p>
        </div>
        <div className="min-w-0 text-sm">
          <p className="font-semibold">Contacto</p>
          <p className="mt-2 text-piedra">{c?.contacto_direccion}</p>
          <p className="text-piedra">{c?.contacto_telefono}</p>
          <p className="break-words text-piedra">{c?.contacto_correo}</p>
          <p className="break-words text-piedra">{c?.contacto_web}</p>
        </div>
        <div className="min-w-0 text-sm">
          <p className="font-semibold">Fuentes y método</p>
          <p className="mt-2 text-piedra">Reportes mensuales de los alojamientos asociados y población del Censo 2022 (INEC).</p>
          <p className="mt-2 text-piedra">Definiciones de IRTS 2008, Eurostat, ETIS 2016 y CoStar/STR.</p>
        </div>
      </div>
      <div className="bandera" aria-hidden />
    </footer>
  )
}
