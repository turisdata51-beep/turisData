import { useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import {
  Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import { EncabezadoPublico } from '../../componentes/EncabezadoPublico'
import { Estado } from '../../componentes/Estado'
import { Placa, TarjetaKpi } from '../../componentes/Indicador'
import { PiePublico } from '../../componentes/PiePublico'
import { api } from '../../lib/api'
import { fechaHora, mes, numero } from '../../lib/formato'
import { ejes, tooltip } from '../../lib/graficos'
import type { Resumen } from '../../lib/tipos'

type Serie = { periodo: string; [codigo: string]: number | string }
type Parroquia = { parroquia: string; tipo: string; confidencial: boolean; A1?: number; A2?: number; B4?: number }
type Filtros = { periodos: string[]; zonas: string[]; categorias: string[] }

const CANTON = 'Cuenca'

/** Parámetros de filtro para la API (zona o categoría; la categoría solo existe a nivel cantonal). */
function consulta(zona: string, categoria: string) {
  const p = new URLSearchParams()
  if (categoria) p.set('categoria', categoria)
  else if (zona !== CANTON) p.set('zona', zona)
  return p
}

function Selector({ id, etiqueta, valor, alCambiar, opciones, deshabilitado = false }: {
  id: string; etiqueta: string; valor: string; alCambiar: (v: string) => void
  opciones: { valor: string; texto: string }[]; deshabilitado?: boolean
}) {
  return (
    <label className="grid min-w-0 gap-1 text-sm" htmlFor={id}>
      <span className="font-semibold">{etiqueta}</span>
      <select id={id} className="campo" value={valor} disabled={deshabilitado} onChange={e => alCambiar(e.target.value)}>
        {opciones.map(o => <option key={o.valor} value={o.valor}>{o.texto}</option>)}
      </select>
    </label>
  )
}

export default function Observatorio() {
  const [parametros, setParametros] = useSearchParams()
  const [filtros, setFiltros] = useState<Filtros | null>(null)
  const [resumen, setResumen] = useState<Resumen | null>(null)
  const [serie, setSerie] = useState<Serie[]>([])
  const [residencia, setResidencia] = useState<Serie[]>([])
  const [parroquias, setParroquias] = useState<Parroquia[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => { api<Filtros>('/public/filtros').then(setFiltros).catch(e => setError(e.message)) }, [])

  // Los filtros viven en la dirección (?mes=…&zona=…&categoria=…&desde=…&hasta=…) para poder compartirlos
  const periodos = filtros?.periodos ?? []
  const ultimo = periodos[periodos.length - 1] ?? ''
  const periodo = parametros.get('mes') ?? ultimo
  const categoria = parametros.get('categoria') ?? ''
  const zona = categoria ? CANTON : (parametros.get('zona') ?? CANTON)
  const hasta = parametros.get('hasta') ?? ultimo
  const desde = parametros.get('desde') ?? periodos[Math.max(0, periodos.length - 12)] ?? ''

  function cambiar(cambios: Record<string, string>) {
    const nuevo = new URLSearchParams(parametros)
    for (const [clave, valor] of Object.entries(cambios)) {
      if (valor) nuevo.set(clave, valor)
      else nuevo.delete(clave)
    }
    setParametros(nuevo, { replace: true })
  }

  const filtro = consulta(zona, categoria).toString()
  useEffect(() => {
    if (!periodo) return
    const q = filtro ? `&${filtro}` : ''
    api<Resumen>(`/public/resumen?periodo=${periodo}${q}`).then(setResumen).catch(e => setError(e.message))
    api<{ parroquias: Parroquia[] }>(`/public/parroquias?periodo=${periodo}`).then(d => setParroquias(d.parroquias))
      .catch(e => setError(e.message))
  }, [periodo, filtro])

  useEffect(() => {
    if (!filtros) return
    const q = filtro ? `&${filtro}` : ''
    api<Serie[]>(`/public/series?codigos=B4,A2${q}`).then(setSerie).catch(e => setError(e.message))
    // La residencia no se calcula por categoría; con categoría la página muestra un aviso en su lugar
    if (!categoria) api<Serie[]>(`/public/residencia?codigo=A2${q}`).then(setResidencia).catch(e => setError(e.message))
  }, [filtros, filtro, categoria])

  // Ocupación del año del mes elegido contra el año anterior, mes a mes
  const comparacion = useMemo(() => {
    if (!periodo) return []
    const anio = Number(periodo.slice(0, 4))
    const porClave = new Map(serie.map(s => [String(s.periodo).slice(0, 7), s]))
    return Array.from({ length: 12 }, (_, i) => {
      const m = String(i + 1).padStart(2, '0')
      return {
        mes: mes(`${anio}-${m}`, true).split(' ')[0],
        actual: porClave.get(`${anio}-${m}`)?.B4 as number | undefined,
        anterior: porClave.get(`${anio - 1}-${m}`)?.B4 as number | undefined,
      }
    })
  }, [serie, periodo])

  const residenciaEnRango = residencia.filter(r => String(r.periodo) >= desde && String(r.periodo) <= hasta)
  const publicadas = parroquias.filter(p => !p.confidencial)
  const confidenciales = parroquias.filter(p => p.confidencial)
  const maxNoches = Math.max(1, ...publicadas.map(p => p.A2 ?? 0))
  const anio = periodo.slice(0, 4)
  const alcance = categoria ? `Alojamientos de ${categoria} del cantón Cuenca`
    : zona === CANTON ? 'Alojamientos formales del cantón Cuenca' : `Alojamientos formales de la parroquia ${zona}`
  const opcionesMes = [...periodos].reverse().map(p => ({ valor: p, texto: mes(p) }))
  const reportaron = resumen?.kpis.find(k => k.codigo === 'A1')

  return (
    <div className="min-h-screen bg-fondo">
      <EncabezadoPublico />

      <section className="border-b border-linea bg-papel">
        <div className="marco space-y-6 py-8">
          <div className="min-w-0">
            <h1 className="text-[clamp(1.9rem,4vw,3rem)]">Indicadores de {mes(periodo)}</h1>
            <p className="mt-2 max-w-[60ch] text-piedra">{alcance} que reportan cada mes a la Cámara.</p>
            <p className="mt-2 text-sm text-piedra">
              Actualizado el {fechaHora(resumen?.ultima_actualizacion)} <span className="pastilla ml-1 text-alerta">datos de demostración</span>
            </p>
          </div>

          <form className="grid gap-3 sm:grid-cols-2 lg:grid-cols-[1fr_1fr_1fr_auto]" aria-label="Filtros" onSubmit={e => e.preventDefault()}>
            <Selector id="filtro-mes" etiqueta="Mes" valor={periodo} alCambiar={v => cambiar({ mes: v })} opciones={opcionesMes} />
            <Selector id="filtro-zona" etiqueta="Zona" valor={zona} deshabilitado={Boolean(categoria)}
              alCambiar={v => cambiar({ zona: v === CANTON ? '' : v })}
              opciones={(filtros?.zonas ?? [CANTON]).map(z => ({ valor: z, texto: z === CANTON ? 'Cantón Cuenca' : z }))} />
            <Selector id="filtro-categoria" etiqueta="Categoría" valor={categoria}
              alCambiar={v => cambiar({ categoria: v, zona: '' })}
              opciones={[{ valor: '', texto: 'Todas' }, ...(filtros?.categorias ?? []).map(c => ({ valor: c, texto: c }))]} />
            <div className="flex items-end">
              <button type="button" className="boton-sec w-full justify-center" onClick={() => setParametros({}, { replace: true })}>
                Quitar filtros
              </button>
            </div>
          </form>
          <p className="text-xs text-piedra">
            Solo aparecen las zonas y categorías con al menos 3 establecimientos que reportan. La categoría se muestra para todo el cantón.
          </p>
        </div>
      </section>

      <main className="marco space-y-12 py-10">
        <Estado cargando={!resumen && !error} error={error}>
          <section aria-label="Indicadores del mes" className="lechada sm:grid-cols-2 lg:grid-cols-4">
            {resumen?.kpis.map(k => <TarjetaKpi key={k.codigo} kpi={k} />)}
          </section>
          {reportaron?.n_unidades != null && (
            <p className="text-sm text-piedra">
              Reportaron {reportaron.n_unidades} establecimientos
              {reportaron.cobertura_pct !== null && ` (${numero(reportaron.cobertura_pct, 0)} % de los participantes)`}.
              ADR y RevPAR se calculan solo con los {resumen?.kpis.find(k => k.codigo === 'B6')?.n_unidades ?? 0} que comparten ingresos.
            </p>
          )}

          <section className="grid gap-6 lg:grid-cols-2">
            <figure className="min-w-0 border border-linea bg-papel p-4">
              <figcaption className="flex flex-wrap items-center gap-2">
                <Placa codigo="B4" /><span className="font-display text-lg font-semibold">Ocupación: {anio} frente a {Number(anio) - 1}</span>
              </figcaption>
              <div className="mt-4 h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={comparacion} margin={{ top: 8, right: 12, left: -14, bottom: 0 }}>
                    <CartesianGrid stroke="var(--linea)" strokeDasharray="2 4" vertical={false} />
                    <XAxis dataKey="mes" {...ejes} axisLine={{ stroke: 'var(--linea)' }} />
                    <YAxis {...ejes} axisLine={false} domain={[30, 80]} ticks={[30, 40, 50, 60, 70, 80]} unit=" %" width={56} allowDataOverflow />
                    <Tooltip contentStyle={tooltip} formatter={v => `${numero(Number(v), 1)} %`} />
                    <Legend wrapperStyle={{ fontSize: 12, color: 'var(--piedra)' }} />
                    <Line name={String(Number(anio) - 1)} dataKey="anterior" stroke="var(--oro)" strokeWidth={2} strokeDasharray="5 4" dot={false} isAnimationActive={false} />
                    <Line name={anio} dataKey="actual" stroke="var(--rojo)" strokeWidth={2.5} dot={{ r: 3, fill: 'var(--rojo)' }} isAnimationActive={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </figure>

            <figure className="min-w-0 border border-linea bg-papel p-4">
              <figcaption className="flex flex-wrap items-center justify-between gap-3">
                <span className="flex items-center gap-2"><Placa codigo="A2" /><span className="font-display text-lg font-semibold">Pernoctaciones por residencia</span></span>
                <span className="flex items-center gap-2 text-sm">
                  <label className="sr-only" htmlFor="filtro-desde">Desde</label>
                  <select id="filtro-desde" className="campo !w-auto !py-1 !text-sm" value={desde} onChange={e => cambiar({ desde: e.target.value })}>
                    {periodos.filter(p => p <= hasta).map(p => <option key={p} value={p}>{mes(p, true)}</option>)}
                  </select>
                  <span className="text-piedra">a</span>
                  <label className="sr-only" htmlFor="filtro-hasta">Hasta</label>
                  <select id="filtro-hasta" className="campo !w-auto !py-1 !text-sm" value={hasta} onChange={e => cambiar({ hasta: e.target.value })}>
                    {periodos.filter(p => p >= desde).map(p => <option key={p} value={p}>{mes(p, true)}</option>)}
                  </select>
                </span>
              </figcaption>
              <div className="mt-4 h-72">
                {categoria ? (
                  <p className="grid h-full place-items-center text-center text-sm text-piedra">La residencia de los huéspedes se publica por zona, no por categoría.</p>
                ) : (
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={residenciaEnRango} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
                      <CartesianGrid stroke="var(--linea)" strokeDasharray="2 4" vertical={false} />
                      <XAxis dataKey="periodo" tickFormatter={p => mes(p, true)} {...ejes} axisLine={{ stroke: 'var(--linea)' }} minTickGap={12} />
                      <YAxis {...ejes} axisLine={false} tickFormatter={v => numero(v)} width={56} />
                      <Tooltip contentStyle={tooltip} labelFormatter={p => mes(String(p))} formatter={v => numero(Number(v))} />
                      <Legend wrapperStyle={{ fontSize: 12, color: 'var(--piedra)' }} />
                      <Bar name="Residentes en Ecuador" dataKey="residente" stackId="r" fill="var(--rojo)" isAnimationActive={false} />
                      <Bar name="No residentes" dataKey="no_residente" stackId="r" fill="var(--oro)" isAnimationActive={false} />
                    </BarChart>
                  </ResponsiveContainer>
                )}
              </div>
            </figure>
          </section>

          <section className="border border-linea bg-papel">
            <div className="flex flex-wrap items-baseline justify-between gap-2 border-b border-linea p-4">
              <h2 className="text-xl">Por parroquia en {mes(periodo)}</h2>
              <p className="text-sm text-piedra">Todo el cantón, ordenadas por pernoctaciones.</p>
            </div>
            <div className="overflow-x-auto">
              <table className="tabla min-w-[560px]">
                <thead>
                  <tr><th>Parroquia</th><th>Pernoctaciones</th><th className="text-right">Llegadas</th><th className="text-right">Ocupación</th></tr>
                </thead>
                <tbody>
                  {publicadas.map(p => (
                    <tr key={p.parroquia} className={p.parroquia === zona ? 'bg-rojo-suave' : ''}>
                      <td>
                        <button type="button" className="text-left font-semibold hover:text-rojo" onClick={() => cambiar({ zona: p.parroquia, categoria: '' })}>
                          {p.parroquia}
                        </button>{' '}
                        <span className="text-xs text-piedra">{p.tipo}</span>
                      </td>
                      <td className="w-[40%]">
                        <div className="flex items-center gap-3">
                          <div className="h-2.5 flex-1 bg-suave"><div className="h-full bg-rojo" style={{ width: `${(p.A2 ?? 0) / maxNoches * 100}%` }} /></div>
                          <span className="numero w-16 text-right">{numero(p.A2)}</span>
                        </div>
                      </td>
                      <td className="numero text-right">{numero(p.A1)}</td>
                      <td className="numero text-right">{numero(p.B4, 1)} %</td>
                    </tr>
                  ))}
                  {confidenciales.length > 0 && (
                    <tr>
                      <td colSpan={4} className="text-sm text-piedra">
                        <span className="pastilla mr-2">confidencial</span>
                        {confidenciales.map(p => p.parroquia).join(', ')}: tienen menos de 3 establecimientos reportantes y sus cifras se incluyen solo en el total cantonal.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </section>

          <section className="grid gap-6 text-sm text-piedra sm:grid-cols-3">
            <p><strong className="text-tinta">Universo.</strong> Alojamientos formales asociados que reportan cada mes. No incluye alquileres de corta estancia ni visitantes del día.</p>
            <p><strong className="text-tinta">Comparabilidad.</strong> La ocupación por habitaciones no se mezcla con la ocupación por plazas ni con la de plataformas de alquiler.</p>
            <p><strong className="text-tinta">Definiciones.</strong> Cada indicador tiene una ficha con fórmula y fuente en <Link to="/metodologia" className="text-rojo underline">Metodología</Link>.</p>
          </section>
        </Estado>
      </main>
      <PiePublico />
    </div>
  )
}
