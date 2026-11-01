import type { ReactNode } from 'react'

/** Encabezado de cada sección del panel: título, descripción y acciones a la derecha. */
export function TituloSeccion({ titulo, descripcion, children }: { titulo: string; descripcion?: string; children?: ReactNode }) {
  return (
    <header className="flex flex-wrap items-end justify-between gap-4">
      <div className="min-w-0">
        <h1 className="text-[clamp(1.6rem,3vw,2.2rem)]">{titulo}</h1>
        {descripcion && <p className="mt-1 max-w-[70ch] text-piedra">{descripcion}</p>}
      </div>
      {children && <div className="flex flex-wrap gap-2">{children}</div>}
    </header>
  )
}
