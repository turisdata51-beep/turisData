import { useEffect, useState, type ReactNode } from 'react'
import { Link, NavLink } from 'react-router-dom'
import { api, unidadCorta, valorKpi, type Contenido, type Kpi } from './api'

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

export function EncabezadoPublico() {
  const enlace = ({ isActive }: { isActive: boolean }) =>
    `py-1 text-sm font-semibold border-b-2 ${isActive ? 'border-rojo text-tinta' : 'border-transparent text-piedra hover:text-tinta'}`
  return (
    <header className="relative z-20 border-b border-linea bg-fondo/95 backdrop-blur sm:sticky" style={{ top: 'env(safe-area-inset-top, 0px)' }}>
      <div className="marco flex flex-wrap items-center justify-between gap-x-6 gap-y-3 py-3">
        <Marca />
        <nav className="flex flex-wrap items-center gap-x-5 gap-y-2">
          <NavLink to="/" end className={enlace}>Inicio</NavLink>
          <NavLink to="/observatorio" className={enlace}>Observatorio</NavLink>
          <NavLink to="/metodologia" className={enlace}>Metodología</NavLink>
          <Link to="/admin" className="boton-sec !py-1.5 text-sm">Ingresar</Link>
        </nav>
      </div>
    </header>
  )
}

export function Placa({ codigo }: { codigo: string }) {
  return <span className="placa" title={`Indicador ${codigo}`}>{codigo}</span>
}

export function Variacion({ valor }: { valor: number | null }) {
  if (valor === null) return <span className="text-sm text-piedra">sin comparación</span>
  const sube = valor >= 0
  return (
    <span className={`text-sm ${sube ? 'text-rio' : 'text-critico'}`}>
      {sube ? '+' : '−'}{Math.abs(valor).toLocaleString('es-EC', { maximumFractionDigits: 1 })} % frente al año anterior
    </span>
  )
}

/** Pieza de la rejilla de indicadores. Va dentro de un contenedor .lechada, que pone las juntas. */
export function TarjetaKpi({ kpi }: { kpi: Kpi }) {
  const unidad = unidadCorta(kpi.unidad)
  return (
    <article className="flex flex-col gap-3 p-5">
      <div className="flex items-start justify-between gap-3">
        <Placa codigo={kpi.codigo} />
        {kpi.bandera === 'estimado' && <span className="pastilla text-alerta" title="Usa la población del último censo disponible">estimado</span>}
      </div>
      <h3 className="font-texto text-[0.95rem] font-semibold leading-snug tracking-normal text-piedra">{kpi.nombre}</h3>
      <div className="mt-auto">
        <p className="cifra text-[2.3rem] text-tinta">{valorKpi(kpi.valor, kpi.unidad)}</p>
        <p className="mt-1 min-h-5 text-sm text-piedra">{unidad}</p>
      </div>
      <Variacion valor={kpi.variacion_interanual} />
    </article>
  )
}

export function Estado({ cargando, error, children }: { cargando: boolean; error: string | null; children: ReactNode }) {
  if (error) return <p className="border border-critico/40 bg-papel p-4 text-critico" role="alert">{error}</p>
  if (cargando) return <p className="p-4 text-piedra">Cargando datos…</p>
  return <>{children}</>
}

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
