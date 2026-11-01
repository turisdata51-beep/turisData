/** Botón hamburguesa: tres líneas que se convierten en una X al abrir. */
export function BotonMenu({ abierto, alternar, controla, className = '' }: {
  abierto: boolean; alternar: () => void; controla: string; className?: string
}) {
  const linea = 'absolute left-1/2 h-0.5 w-5 -translate-x-1/2 rounded bg-tinta transition-transform duration-200 motion-reduce:transition-none'
  return (
    <button type="button" onClick={alternar} aria-expanded={abierto} aria-controls={controla}
      aria-label={abierto ? 'Cerrar menú' : 'Abrir menú'}
      className={`relative size-10 shrink-0 rounded-md border border-linea ${className}`}>
      <span className={`${linea} ${abierto ? 'top-1/2 rotate-45' : 'top-[13px]'}`} />
      <span className={`${linea} top-1/2 ${abierto ? 'opacity-0' : ''}`} />
      <span className={`${linea} ${abierto ? 'top-1/2 -rotate-45' : 'top-[25px]'}`} />
    </button>
  )
}
