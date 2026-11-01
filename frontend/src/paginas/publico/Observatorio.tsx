import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import { EncabezadoPublico } from '../../componentes/EncabezadoPublico'
import { Estado } from '../../componentes/Estado'
import { Placa, TarjetaKpi } from '../../componentes/Indicador'
import { PiePublico } from '../../componentes/PiePublico'
import { api } from '../../lib/api'
import { fechaHora, mes, numero } from '../../lib/formato'
import type { Resumen } from '../../lib/tipos'

type Serie = { periodo: string; [codigo: string]: number | string }
type Parroquia = { parroquia: string; tipo: string; confidencial: boolean; A1?: number; A2?: number; B4?: number }

const ejes = { tick: { fill: 'var(--piedra)', fontSize: 11 }, tickLine: false }
const tooltip = { background: 'var(--papel)', border: '1px solid var(--linea)', color: 'var(--tinta)', fontSize: 13 }

export default function Observatorio() {
  const [periodos, setPeriodos] = useState<string[]>([])
  const [periodo, setPeriodo] = useState<string>('')
  const [resumen, setResumen] = useState<Resumen | null>(null)
  const [serie, setSerie] = useState<Serie[]>([])
  const [residencia, setResidencia] = useState<Serie[]>([])
  const [parroquias, setParroquias] = useState<Parroquia[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api<string[]>('/public/periodos').then(p => { setPeriodos(p); setPeriodo(p[p.length - 1] ?? '') })
      .catch(e => setError(e.message))
    api<Serie[]>('/public/series?codigos=B4,A2,B6').then(setSerie).catch(e => setError(e.message))
    api<Serie[]>('/public/residencia?codigo=A2').then(setResidencia).catch(e => setError(e.message))
  }, [])

  useEffect(() => {
    if (!periodo) return
    api<Resumen>(`/public/resumen?periodo=${periodo}`).then(setResumen).catch(e => setError(e.message))
    api<{ parroquias: Parroquia[] }>(`/public/parroquias?periodo=${periodo}`).then(d => setParroquias(d.parroquias))
      .catch(e => setError(e.message))
  }, [periodo])

  // Ocupación del año en curso contra el año anterior, mes a mes
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

  const publicadas = parroquias.filter(p => !p.confidencial)
  const confidenciales = parroquias.filter(p => p.confidencial)
  const maxNoches = Math.max(1, ...publicadas.map(p => p.A2 ?? 0))
  const anio = periodo.slice(0, 4)

  return (
    <div className="min-h-screen bg-fondo">
      <EncabezadoPublico />

      <section className="border-b border-linea bg-papel">
        <div className="marco flex flex-wrap items-end justify-between gap-6 py-8">
          <div className="min-w-0">
                        <h1 className="text-[clamp(1.9rem,4vw,3rem)]">Indicadores de {mes(periodo)}</h1>
            <p className="mt-2 max-w-[60ch] text-piedra">Alojamientos formales del cantón Cuenca que reportan cada mes a la Cámara.</p>
            <p className="mt-2 text-sm text-piedra">
              Actualizado el {fechaHora(resumen?.ultima_actualizacion)} <span className="pastilla ml-1 text-alerta">datos de demostración</span>
            </p>
          </div>
          <label className="grid gap-1 text-sm" htmlFor="periodo">
            <span className="font-semibold">Mes</span>
            <select id="periodo" className="campo min-w-48" value={periodo} onChange={e => setPeriodo(e.target.value)}>
              {[...periodos].reverse().map(p => <option key={p} value={p}>{mes(p)}</option>)}
            </select>
          </label>
        </div>
      </section>

      <main className="marco space-y-12 py-10">
        <Estado cargando={!resumen && !error} error={error}>
          <section aria-label="Indicadores del mes" className="lechada sm:grid-cols-2 lg:grid-cols-4">
            {resumen?.kpis.map(k => <TarjetaKpi key={k.codigo} kpi={k} />)}
          </section>
          {resumen && resumen.kpis[0]?.cobertura_pct !== null && (
            <p className="text-sm text-piedra">
              Reportaron {resumen.kpis[0].n_unidades} establecimientos ({numero(resumen.kpis[0].cobertura_pct, 0)} % de los participantes).
              ADR y RevPAR se calculan solo con los {resumen.kpis.find(k => k.codigo === 'B6')?.n_unidades} que comparten ingresos.
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
                    <YAxis {...ejes} axisLine={false} domain={[30, 80]} ticks={[30, 40, 50, 60, 70, 80]} unit=" %" width={56} />
                    <Tooltip contentStyle={tooltip} formatter={v => `${numero(Number(v), 1)} %`} />
                    <Legend wrapperStyle={{ fontSize: 12, color: 'var(--piedra)' }} />
                    <Line name={String(Number(anio) - 1)} dataKey="anterior" stroke="var(--oro)" strokeWidth={2} strokeDasharray="5 4" dot={false} isAnimationActive={false} />
                    <Line name={anio} dataKey="actual" stroke="var(--rojo)" strokeWidth={2.5} dot={{ r: 3, fill: 'var(--rojo)' }} isAnimationActive={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </figure>

            <figure className="min-w-0 border border-linea bg-papel p-4">
              <figcaption className="flex flex-wrap items-center gap-2">
                <Placa codigo="A2" /><span className="font-display text-lg font-semibold">Pernoctaciones por residencia</span>
              </figcaption>
              <div className="mt-4 h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={residencia.slice(-12)} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
                    <CartesianGrid stroke="var(--linea)" strokeDasharray="2 4" vertical={false} />
                    <XAxis dataKey="periodo" tickFormatter={p => mes(p, true)} {...ejes} axisLine={{ stroke: 'var(--linea)' }} />
                    <YAxis {...ejes} axisLine={false} tickFormatter={v => numero(v)} width={56} />
                    <Tooltip contentStyle={tooltip} labelFormatter={p => mes(String(p))} formatter={v => numero(Number(v))} />
                    <Legend wrapperStyle={{ fontSize: 12, color: 'var(--piedra)' }} />
                    <Bar name="Residentes en Ecuador" dataKey="residente" stackId="r" fill="var(--rojo)" isAnimationActive={false} />
                    <Bar name="No residentes" dataKey="no_residente" stackId="r" fill="var(--oro)" isAnimationActive={false} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </figure>
          </section>

          <section className="border border-linea bg-papel">
            <div className="flex flex-wrap items-baseline justify-between gap-2 border-b border-linea p-4">
              <h2 className="text-xl">Por parroquia en {mes(periodo)}</h2>
              <p className="text-sm text-piedra">Ordenadas por pernoctaciones.</p>
            </div>
            <div className="overflow-x-auto">
              <table className="tabla min-w-[560px]">
                <thead>
                  <tr><th>Parroquia</th><th>Pernoctaciones</th><th className="text-right">Llegadas</th><th className="text-right">Ocupación</th></tr>
                </thead>
                <tbody>
                  {publicadas.map(p => (
                    <tr key={p.parroquia}>
                      <td><span className="font-semibold">{p.parroquia}</span> <span className="text-xs text-piedra">{p.tipo}</span></td>
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
