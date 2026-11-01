import type { ReactNode } from 'react'

/** Muestra el error o el aviso de carga; cuando hay datos, muestra el contenido. */
export function Estado({ cargando, error, children }: { cargando: boolean; error: string | null; children: ReactNode }) {
  if (error) return <p className="border border-critico/40 bg-papel p-4 text-critico" role="alert">{error}</p>
  if (cargando) return <p className="p-4 text-piedra">Cargando datos…</p>
  return <>{children}</>
}
