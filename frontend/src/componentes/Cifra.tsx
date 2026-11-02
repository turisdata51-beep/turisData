/** Cifra destacada de una rejilla .lechada: etiqueta, valor grande y una línea de detalle. */
export function Cifra({ etiqueta, valor, detalle, children }: { etiqueta: string; valor: string; detalle: string; children?: React.ReactNode }) {
  return (
    <article className="flex flex-col gap-2 p-5">
      <h3 className="font-texto text-[0.95rem] font-semibold tracking-normal text-piedra">{etiqueta}</h3>
      <p className="cifra mt-auto text-[2.1rem] text-tinta">{valor}</p>
      <p className="text-sm text-piedra">{detalle}</p>
      {children}
    </article>
  )
}
