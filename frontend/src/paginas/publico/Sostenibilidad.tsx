import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import { Cifra } from '../../componentes/Cifra'
import { EncabezadoPublico } from '../../componentes/EncabezadoPublico'
import { Estado } from '../../componentes/Estado'
import { Placa, Variacion } from '../../componentes/Indicador'
import { PiePublico } from '../../componentes/PiePublico'
import { api } from '../../lib/api'
import { fecha, mes, numero, trimestre, valorKpi } from '../../lib/formato'
import { ejes, tooltip } from '../../lib/graficos'

type Punto = { periodo: string; valor: number | null; n_unidades: number }
type Indicador = {
  codigo: string; nombre: string; unidad: string; periodicidad: string; definicion: string; limitaciones: string
  ultimo: Punto | null; serie: Punto[]
}
type Respuesta = { indicadores: Indicador[]; actualizado: string | null }

/** Variación frente al mismo período del año anterior; null si no hay base comparable. */
function variacion(ind: Indicador | undefined): number | null {
  const u = ind?.ultimo
  if (!u?.valor) return null
  const anterior = `${Number(u.periodo.slice(0, 4)) - 1}${u.periodo.slice(4)}`
  const base = ind!.serie.find(s => s.periodo === anterior)?.valor
  return base ? Math.round((u.valor - base) / base * 1000) / 10 : null
}

const anio = (periodo: string | undefined) => periodo?.slice(0, 4) ?? '—'
const reportan = (p: Punto | null | undefined, que: string) => (p ? `${p.n_unidades} ${que}` : 'sin datos publicables')

/** Gráfico pequeño de un indicador mensual; los meses confidenciales quedan como hueco. */
function Mensual({ ind }: { ind: Indicador }) {
  return (
    <figure className="min-w-0 border border-linea bg-papel p-4">
      <figcaption className="flex items-baseline gap-2 font-display text-base font-semibold"><Placa codigo={ind.codigo} />{ind.nombre}</figcaption>
      <p className="text-sm text-piedra">En {ind.unidad}, cada mes.</p>
      <div className="mt-3 h-48">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={ind.serie} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid stroke="var(--linea)" strokeDasharray="2 4" vertical={false} />
            <XAxis dataKey="periodo" tickFormatter={p => mes(String(p), true)} {...ejes} axisLine={{ stroke: 'var(--linea)' }} minTickGap={24} />
            <YAxis {...ejes} axisLine={false} width={44} tickFormatter={v => numero(Number(v), ind.unidad.startsWith('kg') ? 1 : 0)} />
            <Tooltip contentStyle={tooltip} labelFormatter={p => mes(String(p))}
              formatter={v => [v === null ? 'confidencial' : `${valorKpi(Number(v), ind.unidad)} ${ind.unidad}`, ind.nombre]} />
            <Line type="monotone" dataKey="valor" stroke="var(--rojo)" strokeWidth={1.8} dot={false} connectNulls={false} isAnimationActive={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </figure>
  )
}

export default function Sostenibilidad() {
  const [datos, setDatos] = useState<Respuesta | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api<Respuesta>('/public/sostenibilidad').then(setDatos).catch(e => setError(e.message))
  }, [])

  const ind = Object.fromEntries((datos?.indicadores ?? []).map(i => [i.codigo, i]))
  const { D3: d3, E1: e1, E6: e6, E3: e3, E4: e4, E5: e5 } = ind
  const sinDatos = datos !== null && datos.indicadores.every(i => !i.ultimo)
  const anual = (e1?.serie ?? []).map(s => ({
    anio: anio(s.periodo), E1: s.valor, E6: e6?.serie.find(x => x.periodo === s.periodo)?.valor ?? null,
  }))

  return (
    <div className="min-h-screen bg-fondo">
      <EncabezadoPublico />

      <section className="border-b border-linea bg-papel">
        <div className="marco py-8">
          <h1 className="text-[clamp(1.9rem,4vw,3rem)]">Sostenibilidad y empleo</h1>
          {d3?.ultimo && e3?.ultimo && (
            <p className="mt-3 max-w-[62ch] text-lg">
              En el trimestre de {trimestre(d3.ultimo.periodo)}, el {valorKpi(d3.ultimo.valor, '%')} del empleo en los
              alojamientos asociados fue por temporada. En {mes(e3.ultimo.periodo)}, cada noche de un huésped consumió en promedio{' '}
              {valorKpi(e3.ultimo.valor, e3.unidad)} litros de agua
              {e4?.ultimo?.periodo === e3.ultimo.periodo && <> y {valorKpi(e4.ultimo.valor, e4.unidad)} kWh de electricidad</>}.
            </p>
          )}
          <p className="mt-2 max-w-[70ch] text-sm text-piedra">
            Datos que reportan a la Cámara los establecimientos asociados. Describen a quienes reportan, no a todo el cantón,
            y no se publican cuando reportan menos de 3 establecimientos.
          </p>
        </div>
      </section>

      <main className="marco space-y-14 py-10">
        <Estado cargando={!datos && !error} error={error}>
          {sinDatos && (
            <p className="border border-linea bg-papel p-6 text-piedra">
              Todavía no hay reportes de empleo, accesibilidad ni consumos con suficientes establecimientos para publicarlos.
            </p>
          )}

          {d3 && (
            <section className="space-y-6" aria-labelledby="titulo-empleo">
              <div>
                <h2 id="titulo-empleo" className="text-2xl">Empleo en los alojamientos</h2>
                <p className="mt-1 max-w-[70ch] text-piedra">{d3.definicion}</p>
              </div>
              <div className="grid gap-6 lg:grid-cols-[1fr_2fr]">
                <div className="lechada">
                  <Cifra etiqueta={`Empleo estacional, ${trimestre(d3.ultimo?.periodo)}`} valor={valorKpi(d3.ultimo?.valor ?? null, '%')}
                    detalle={`del empleo; reportan ${reportan(d3.ultimo, 'establecimientos')}`}>
                    <Variacion valor={variacion(d3)} />
                  </Cifra>
                </div>
                <figure className="min-w-0 border border-linea bg-papel p-4">
                  <figcaption className="font-display text-lg font-semibold">Empleo estacional por trimestre</figcaption>
                  <p className="text-sm text-piedra">Porcentaje de las personas empleadas con contrato por temporada.</p>
                  <div className="mt-4 h-60">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={d3.serie} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                        <CartesianGrid stroke="var(--linea)" strokeDasharray="2 4" vertical={false} />
                        <XAxis dataKey="periodo" tickFormatter={p => trimestre(String(p), true)} {...ejes} axisLine={{ stroke: 'var(--linea)' }} />
                        <YAxis {...ejes} axisLine={false} width={48} unit=" %" />
                        <Tooltip contentStyle={tooltip} labelFormatter={p => trimestre(String(p))}
                          formatter={v => [v === null ? 'confidencial' : valorKpi(Number(v), '%'), 'Empleo estacional']} />
                        <Bar dataKey="valor" fill="var(--rojo)" isAnimationActive={false} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </figure>
              </div>
            </section>
          )}

          {e1 && e6 && (
            <section className="space-y-6" aria-labelledby="titulo-accesibilidad">
              <div>
                <h2 id="titulo-accesibilidad" className="text-2xl">Accesibilidad y certificaciones</h2>
                <p className="mt-1 max-w-[70ch] text-piedra">
                  Reporte anual de cada establecimiento: habitaciones revisadas y accesibles, y certificación de calidad o sostenibilidad vigente.
                </p>
              </div>
              <div className="grid gap-6 lg:grid-cols-[1fr_2fr]">
                <div className="lechada">
                  <Cifra etiqueta={`Habitaciones accesibles, ${anio(e1.ultimo?.periodo)}`} valor={valorKpi(e1.ultimo?.valor ?? null, '%')}
                    detalle={`de las habitaciones revisadas en ${reportan(e1.ultimo, 'establecimientos')}`}>
                    <Variacion valor={variacion(e1)} />
                  </Cifra>
                  <Cifra etiqueta={`Con certificación vigente, ${anio(e6.ultimo?.periodo)}`} valor={valorKpi(e6.ultimo?.valor ?? null, '%')}
                    detalle={`de ${reportan(e6.ultimo, 'establecimientos que reportan')}`}>
                    <Variacion valor={variacion(e6)} />
                  </Cifra>
                </div>
                <figure className="min-w-0 border border-linea bg-papel p-4">
                  <figcaption className="font-display text-lg font-semibold">Evolución por año</figcaption>
                  <p className="text-sm text-piedra">Porcentajes; cada año cuenta a los establecimientos que reportaron ese año.</p>
                  <div className="mt-4 h-60">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={anual} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                        <CartesianGrid stroke="var(--linea)" strokeDasharray="2 4" vertical={false} />
                        <XAxis dataKey="anio" {...ejes} axisLine={{ stroke: 'var(--linea)' }} />
                        <YAxis {...ejes} axisLine={false} width={48} unit=" %" />
                        <Tooltip contentStyle={tooltip} formatter={(v, n) => [v === null ? 'confidencial' : valorKpi(Number(v), '%'), n]} />
                        <Legend wrapperStyle={{ fontSize: 13 }} />
                        <Bar dataKey="E1" name="Habitaciones accesibles" fill="var(--rojo)" isAnimationActive={false} />
                        <Bar dataKey="E6" name="Con certificación" fill="var(--oro)" isAnimationActive={false} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </figure>
              </div>
            </section>
          )}

          {e3 && e4 && e5 && (
            <section className="space-y-6" aria-labelledby="titulo-consumos">
              <div>
                <h2 id="titulo-consumos" className="text-2xl">Consumo por noche turística</h2>
                <p className="mt-1 max-w-[70ch] text-piedra">
                  Agua, electricidad y residuos de los alojamientos divididos para las noches de sus huéspedes en el mismo mes.
                  Cada medida usa solo los establecimientos que la reportaron.
                </p>
              </div>
              <div className="lechada sm:grid-cols-3">
                {[e3, e4, e5].map(i => (
                  <Cifra key={i.codigo} etiqueta={`${i.nombre}, ${mes(i.ultimo?.periodo)}`}
                    valor={valorKpi(i.ultimo?.valor ?? null, i.unidad)} detalle={`${i.unidad}; ${reportan(i.ultimo, 'establecimientos')}`}>
                    <Variacion valor={variacion(i)} menorEsMejor />
                  </Cifra>
                ))}
              </div>
              <div className="grid gap-6 lg:grid-cols-3">
                {[e3, e4, e5].map(i => <Mensual key={i.codigo} ind={i} />)}
              </div>
            </section>
          )}

          {datos && !sinDatos && (
            <section className="space-y-4" aria-labelledby="titulo-limites">
              <h2 id="titulo-limites" className="text-xl">Cómo leer estos datos</h2>
              <dl className="grid gap-x-8 gap-y-4 text-sm sm:grid-cols-2">
                {datos.indicadores.map(i => (
                  <div key={i.codigo}>
                    <dt className="flex items-baseline gap-2 font-semibold text-tinta"><Placa codigo={i.codigo} />{i.nombre}</dt>
                    <dd className="mt-1 text-piedra">{i.limitaciones}</dd>
                  </div>
                ))}
              </dl>
              <p className="text-sm text-piedra">
                Fuente: plantillas de empleo, accesibilidad y consumos de la Cámara de Turismo del Azuay, con las noches del reporte
                mensual de alojamiento. Último reporte recibido el {fecha(datos.actualizado)}. Fórmulas en{' '}
                <Link to="/metodologia" className="text-rojo underline">Metodología</Link>.
              </p>
            </section>
          )}
        </Estado>
      </main>
      <PiePublico />
    </div>
  )
}
