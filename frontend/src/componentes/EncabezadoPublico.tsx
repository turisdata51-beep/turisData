import { Link, NavLink } from 'react-router-dom'
import { useMenuMovil } from '../lib/useMenuMovil'
import { BotonMenu } from './BotonMenu'
import { Marca } from './Marca'

const ENLACES = [
  { ruta: '/', texto: 'Inicio', exacto: true },
  { ruta: '/observatorio', texto: 'Observatorio', exacto: false },
  { ruta: '/metodologia', texto: 'Metodología', exacto: false },
]

/** Encabezado del sitio público: menú horizontal en escritorio y hamburguesa en móvil. */
export function EncabezadoPublico() {
  const { abierto, alternar } = useMenuMovil()
  const enlace = ({ isActive }: { isActive: boolean }) =>
    `py-1 text-sm font-semibold border-b-2 ${isActive ? 'border-rojo text-tinta' : 'border-transparent text-piedra hover:text-tinta'}`
  const enlaceMovil = ({ isActive }: { isActive: boolean }) =>
    `block border-l-2 px-3 py-3 font-semibold ${isActive ? 'border-rojo text-tinta' : 'border-transparent text-piedra'}`
  return (
    <header className="sticky z-20 border-b border-linea bg-fondo/95 backdrop-blur" style={{ top: 'env(safe-area-inset-top, 0px)' }}>
      <div className="marco flex items-center justify-between gap-6 py-3">
        <Marca />
        <nav className="hidden items-center gap-x-5 md:flex" aria-label="Secciones">
          {ENLACES.map(e => <NavLink key={e.ruta} to={e.ruta} end={e.exacto} className={enlace}>{e.texto}</NavLink>)}
          <Link to="/admin" className="boton-sec !py-1.5 text-sm">Ingresar</Link>
        </nav>
        <BotonMenu abierto={abierto} alternar={alternar} controla="menu-publico" className="md:hidden" />
      </div>
      <nav id="menu-publico" hidden={!abierto} aria-label="Secciones" className="border-t border-linea md:hidden">
        <div className="marco flex flex-col gap-1 py-3">
          {ENLACES.map(e => <NavLink key={e.ruta} to={e.ruta} end={e.exacto} className={enlaceMovil}>{e.texto}</NavLink>)}
          <Link to="/admin" className="boton-sec mt-2 justify-center">Ingresar al panel</Link>
        </div>
      </nav>
    </header>
  )
}
