import { NavLink, Navigate, Outlet, useLocation } from 'react-router-dom'
import type { Rol } from '../api'
import { Marca } from '../componentes'
import Login from './Login'
import { NOMBRE_ROL, useSesion } from './sesion'

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

export default function LayoutAdmin() {
  const { usuario, cargando, salir } = useSesion()
  const { pathname } = useLocation()

  if (cargando) return <p className="p-8 text-piedra">Cargando…</p>
  if (!usuario) return <Login />

  const visibles = SECCIONES.filter(s => s.roles.includes(usuario.rol))
  const actual = SECCIONES.find(s => s.ruta === pathname)
  if (actual && !actual.roles.includes(usuario.rol)) return <Navigate to={visibles[0].ruta} replace />
  if (pathname === '/admin' && usuario.rol === 'asociado') return <Navigate to="/admin/cargas" replace />

  return (
    <div className="min-h-screen bg-fondo lg:grid lg:grid-cols-[16rem_1fr]">
      <aside className="border-b border-linea bg-papel lg:sticky lg:top-0 lg:h-screen lg:border-b-0 lg:border-r">
        <div className="bandera" aria-hidden />
        <div className="flex flex-col gap-5 p-4 lg:h-[calc(100%-28px)]">
          <Marca compacta />
          <nav className="flex gap-1 overflow-x-auto lg:flex-col" aria-label="Secciones del panel">
            {visibles.map(s => (
              <NavLink key={s.ruta} to={s.ruta} end
                className={({ isActive }) => `whitespace-nowrap rounded-[3px] px-3 py-2 text-sm font-semibold ${isActive ? 'bg-rojo-suave text-rojo' : 'text-tinta hover:bg-suave'}`}>
                {s.texto}
              </NavLink>
            ))}
          </nav>
          <div className="mt-auto hidden space-y-3 border-t border-linea pt-4 text-sm lg:block">
            <div>
              <p className="font-semibold">{usuario.nombre}</p>
              <p className="text-xs text-piedra">{NOMBRE_ROL[usuario.rol]}{usuario.codigo_camara ? ` (${usuario.codigo_camara})` : ''}</p>
            </div>
            <div className="flex flex-wrap gap-2">
              <button type="button" className="boton-sec !px-2.5 !py-1.5 text-xs" onClick={salir}>Cerrar sesión</button>
            </div>
          </div>
        </div>
      </aside>
      <div className="min-w-0">
        <div className="flex items-center justify-between gap-3 border-b border-linea px-4 py-2 text-sm lg:hidden">
          <span>{usuario.nombre}, {NOMBRE_ROL[usuario.rol].toLowerCase()}</span>
          <button type="button" className="boton-sec !px-2.5 !py-1 text-xs" onClick={salir}>Salir</button>
        </div>
        <main className="mx-auto max-w-6xl space-y-8 px-4 py-8 lg:px-8">
          <Outlet />
        </main>
      </div>
    </div>
  )
}

export function Titulo({ titulo, descripcion, children }: { titulo: string; descripcion?: string; children?: React.ReactNode }) {
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
