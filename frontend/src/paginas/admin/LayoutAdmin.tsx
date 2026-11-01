import { NavLink, Navigate, Outlet, useLocation } from 'react-router-dom'
import { BotonMenu } from '../../componentes/BotonMenu'
import { Marca } from '../../componentes/Marca'
import { NOMBRE_ROL, type Rol } from '../../lib/tipos'
import { useMenuMovil } from '../../lib/useMenuMovil'
import { useSesion } from '../../sesion/sesion'
import Login from './Login'

const SECCIONES: { ruta: string; texto: string; roles: Rol[] }[] = [
  { ruta: '/admin', texto: 'Resumen', roles: ['administrador', 'analista', 'consulta'] },
  { ruta: '/admin/cargas', texto: 'Cargas de datos', roles: ['administrador', 'analista', 'asociado'] },
  { ruta: '/admin/mis-reportes', texto: 'Mis reportes', roles: ['asociado'] },
  { ruta: '/admin/establecimientos', texto: 'Establecimientos', roles: ['administrador', 'analista'] },
  { ruta: '/admin/indicadores', texto: 'Indicadores', roles: ['administrador', 'analista', 'consulta'] },
  { ruta: '/admin/usuarios', texto: 'Usuarios', roles: ['administrador'] },
  { ruta: '/admin/contenido', texto: 'Contenido del sitio', roles: ['administrador'] },
  { ruta: '/admin/auditoria', texto: 'Auditoría', roles: ['administrador'] },
]

/** Estructura del panel: barra lateral en escritorio, menú hamburguesa en móvil. */
export default function LayoutAdmin() {
  const { usuario, cargando, salir } = useSesion()
  const { pathname } = useLocation()
  const menu = useMenuMovil()

  if (cargando) return <p className="p-8 text-piedra">Cargando…</p>
  if (!usuario) return <Login />

  const visibles = SECCIONES.filter(s => s.roles.includes(usuario.rol))
  const actual = SECCIONES.find(s => s.ruta === pathname)
  if (actual && !actual.roles.includes(usuario.rol)) return <Navigate to={visibles[0].ruta} replace />
  if (pathname === '/admin' && usuario.rol === 'asociado') return <Navigate to="/admin/cargas" replace />

  const secciones = (
    <ul className="flex flex-col gap-1">
      {visibles.map(s => (
        <li key={s.ruta}>
          <NavLink to={s.ruta} end
            className={({ isActive }) => `block rounded-[3px] px-3 py-2.5 text-sm font-semibold lg:py-2 ${isActive ? 'bg-rojo-suave text-rojo' : 'text-tinta hover:bg-suave'}`}>
            {s.texto}
          </NavLink>
        </li>
      ))}
    </ul>
  )
  const cuenta = (
    <div className="space-y-3 border-t border-linea pt-4 text-sm">
      <div>
        <p className="font-semibold">{usuario.nombre}</p>
        <p className="text-xs text-piedra">{NOMBRE_ROL[usuario.rol]}{usuario.codigo_camara ? ` (${usuario.codigo_camara})` : ''}</p>
      </div>
      <button type="button" className="boton-sec !px-2.5 !py-1.5 text-xs" onClick={salir}>Cerrar sesión</button>
    </div>
  )

  return (
    <div className="min-h-screen bg-fondo lg:grid lg:grid-cols-[16rem_1fr]">
      {/* Escritorio: barra lateral fija */}
      <aside className="hidden border-r border-linea bg-papel lg:sticky lg:top-0 lg:block lg:h-screen">
        <div className="bandera" aria-hidden />
        <div className="flex h-[calc(100%-4px)] flex-col gap-5 p-4">
          <Marca compacta />
          <nav aria-label="Secciones del panel">{secciones}</nav>
          <div className="mt-auto">{cuenta}</div>
        </div>
      </aside>

      {/* Móvil y tablet: barra superior con menú hamburguesa */}
      <header className="sticky z-20 border-b border-linea bg-papel lg:hidden" style={{ top: 'env(safe-area-inset-top, 0px)' }}>
        <div className="bandera" aria-hidden />
        <div className="flex items-center justify-between gap-4 px-4 py-2.5">
          <Marca compacta />
          <BotonMenu abierto={menu.abierto} alternar={menu.alternar} controla="menu-panel" />
        </div>
        <nav id="menu-panel" hidden={!menu.abierto} aria-label="Secciones del panel"
          className="max-h-[calc(100dvh-64px)] overflow-y-auto border-t border-linea px-4 py-3">
          {secciones}
          <div className="mt-3">{cuenta}</div>
        </nav>
      </header>

      <div className="min-w-0">
        <main className="mx-auto max-w-6xl space-y-8 px-4 py-8 lg:px-8">
          <Outlet />
        </main>
      </div>
    </div>
  )
}

