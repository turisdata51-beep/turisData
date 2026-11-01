import { Link } from 'react-router-dom'

/** Logo de TurisData: el pin con la ciudad y el nombre en rojo y dorado. */
export function Marca({ compacta = false }: { compacta?: boolean }) {
  return (
    <Link to="/" className="flex items-center gap-2.5" aria-label="TurisData, ir al inicio">
      <img src="/marca.png" alt="" className="h-10 w-auto" width={46} height={40} />
      <span className="flex flex-col gap-1">
        <img src="/marca-texto.png" alt="TurisData" className="h-[18px] w-auto" width={117} height={18} />
        {!compacta && <span className="hidden text-[0.7rem] leading-none text-piedra sm:block">Observatorio turístico de Cuenca</span>}
      </span>
    </Link>
  )
}
