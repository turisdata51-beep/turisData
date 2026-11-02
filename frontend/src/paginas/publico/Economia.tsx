import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import { Cifra } from '../../componentes/Cifra'
import { EncabezadoPublico } from '../../componentes/EncabezadoPublico'
import { Estado } from '../../componentes/Estado'
import { Variacion } from '../../componentes/Indicador'
import { PiePublico } from '../../componentes/PiePublico'
import { api } from '../../lib/api'
import { fecha, mes, numero } from '../../lib/formato'
import { ejes, tooltip } from '../../lib/graficos'

type Economia = {
  mensual: { periodo: string; ventas: number }[]
  anual: { anio: number; ventas: number; meses: number }[]
  ultimo: { periodo: string; ventas: number; variacion_interanual: number | null; acumulado: number
            acumulado_anterior: number; variacion_acumulada: number | null } | null
  actualizado: string | null
}
type Oferta = {
  catastro: { corte: string | null; actualizado: string | null; por_actividad: { actividad: string; establecimientos: number }[]
              alojamiento_por_clasificacion: { clasificacion: string; establecimientos: number }[]
              alojamiento_por_parroquia: { parroquia: string; tipo: string; alojamientos: number }[] }
  capacidad: { corte: string | null; actualizado: string | null
               total: { establecimientos: number; habitaciones: number; plazas: number } | null
               por_tipo: { tipo: string; establecimientos: number; habitaciones: number; plazas: number }[] }
  plazas_por_100: { valor: number; poblacion: number; bandera: string } | null
}

const millones = (v: number) => `$${numero(v / 1e6, 1)} M`
const titulo = (texto: string) => texto.charAt(0) + texto.slice(1).toLowerCase()

export default function Economia() {
  const [economia, setEconomia] = useState<Economia | null>(null)
  const [oferta, setOferta] = useState<Oferta | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api<Economia>('/public/economia').then(setEconomia).catch(e => setError(e.message))
    api<Oferta>('/public/oferta').then(setOferta).catch(e => setError(e.message))
  }, [])

  const u = economia?.ultimo
  const anioActual = u ? Number(u.periodo.slice(0, 4)) : null
  const anioCompleto = economia?.anual.filter(a => a.meses === 12).at(-1)
  const parroquias = oferta?.catastro.alojamiento_por_parroquia ?? []
  const maxParroquia = Math.max(1, ...parroquias.map(p => p.alojamientos))

  return (
    <div className="min-h-screen bg-fondo">
      <EncabezadoPublico />

      <section className="border-b border-linea bg-papel">
        <div className="marco py-8">
          <h1 className="text-[clamp(1.9rem,4vw,3rem)]">Economía y oferta turística</h1>
          {u && anioActual && (
            <p className="mt-3 max-w-[62ch] text-lg">
              De enero a {mes(u.periodo).split(' ')[0]} de {anioActual}, las ventas de alojamiento y comidas en Cuenca
              suman {millones(u.acumulado)}
              {u.variacion_acumulada !== null && <>, {numero(Math.abs(u.variacion_acumulada), 1)}{' '}% {u.variacion_acumulada >= 0 ? 'más' : 'menos'} que en el mismo periodo de {anioActual - 1}</>}.
            </p>
          )}
          <p className="mt-2 text-sm text-piedra">Datos reales de fuentes públicas, extraídos automáticamente.</p>
        </div>
      </section>

      <main className="marco space-y-14 py-10">
        <Estado cargando={(!economia || !oferta) && !error} error={error}>
          {/* Ventas del sector según el SRI */}
          <section className="space-y-6" aria-labelledby="titulo-ventas">
            <div>
              <h2 id="titulo-ventas" className="text-2xl">Ventas de alojamiento y comidas</h2>
              <p className="mt-1 max-w-[70ch] text-piedra">
                Ventas declaradas al SRI por los negocios de la sección CIIU I del cantón Cuenca. Incluye alojamiento y
                restaurantes, porque el SRI no los publica por separado; es un indicador de actividad, no el gasto de los turistas.
              </p>
            </div>
            {u && (
              <div className="lechada sm:grid-cols-3">
                <Cifra etiqueta={`Ventas de ${mes(u.periodo)}`} valor={millones(u.ventas)} detalle="en el mes">
                  <Variacion valor={u.variacion_interanual} />
                </Cifra>
                <Cifra etiqueta={`Acumulado ${anioActual}`} valor={millones(u.acumulado)} detalle={`enero a ${mes(u.periodo).split(' ')[0]}`}>
                  <Variacion valor={u.variacion_acumulada} />
                </Cifra>
                {anioCompleto && <Cifra etiqueta={`Total ${anioCompleto.anio}`} valor={millones(anioCompleto.ventas)} detalle="último año completo" />}
              </div>
            )}

            <div className="grid gap-6 lg:grid-cols-[1.6fr_1fr]">
              <figure className="min-w-0 border border-linea bg-papel p-4">
                <figcaption className="font-display text-lg font-semibold">Ventas mensuales desde 2018</figcaption>
                <p className="text-sm text-piedra">Millones de dólares. La caída de 2020 corresponde a la pandemia.</p>
                <div className="mt-4 h-72">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={economia?.mensual} margin={{ top: 8, right: 12, left: -8, bottom: 0 }}>
                      <defs>
                        <linearGradient id="relleno-ventas" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor="var(--rojo)" stopOpacity={0.22} />
                          <stop offset="100%" stopColor="var(--rojo)" stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid stroke="var(--linea)" strokeDasharray="2 4" vertical={false} />
                      <XAxis dataKey="periodo" tickFormatter={p => String(p).slice(0, 4)} {...ejes} axisLine={{ stroke: 'var(--linea)' }}
                        ticks={economia?.mensual.filter(m => m.periodo.slice(5, 7) === '01').map(m => m.periodo)} />
                      <YAxis {...ejes} axisLine={false} tickFormatter={v => numero(v / 1e6)} width={40} />
                      <Tooltip contentStyle={tooltip} labelFormatter={p => mes(String(p))} formatter={v => [millones(Number(v)), 'Ventas']} />
                      <Area type="monotone" dataKey="ventas" stroke="var(--rojo)" strokeWidth={1.8} fill="url(#relleno-ventas)" isAnimationActive={false} />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </figure>
              <figure className="min-w-0 border border-linea bg-papel p-4">
                <figcaption className="font-display text-lg font-semibold">Total por año</figcaption>
                <p className="text-sm text-piedra">Millones de dólares; {anioActual} va hasta {u ? mes(u.periodo).split(' ')[0] : ''}.</p>
                <div className="mt-4 h-72">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={economia?.anual} margin={{ top: 8, right: 8, left: -8, bottom: 0 }}>
                      <CartesianGrid stroke="var(--linea)" strokeDasharray="2 4" vertical={false} />
                      <XAxis dataKey="anio" {...ejes} axisLine={{ stroke: 'var(--linea)' }} tickFormatter={a => `'${String(a).slice(2)}`} />
                      <YAxis {...ejes} axisLine={false} tickFormatter={v => numero(v / 1e6)} width={40} />
                      <Tooltip contentStyle={tooltip} formatter={(v, _n, p) => [millones(Number(v)), p.payload.meses < 12 ? `Ventas (${p.payload.meses} meses)` : 'Ventas']} />
                      <Bar dataKey="ventas" fill="var(--rojo)" isAnimationActive={false} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </figure>
            </div>
          </section>

          {/* Oferta registrada */}
          <section className="space-y-6" aria-labelledby="titulo-oferta">
            <div>
              <h2 id="titulo-oferta" className="text-2xl">Oferta de alojamiento registrada</h2>
              <p className="mt-1 max-w-[70ch] text-piedra">
                Establecimientos inscritos en el catastro turístico nacional y capacidad instalada según la base municipal de hostelería.
              </p>
            </div>
            <div className="lechada sm:grid-cols-2 lg:grid-cols-4">
              <Cifra etiqueta="Alojamientos en el catastro" valor={numero(oferta?.catastro.alojamiento_por_clasificacion.reduce((s, c) => s + c.establecimientos, 0))}
                detalle={`corte ${mes(oferta?.catastro.corte)}`} />
              <Cifra etiqueta="Habitaciones instaladas" valor={numero(oferta?.capacidad.total?.habitaciones)} detalle={`base municipal, ${mes(oferta?.capacidad.corte)}`} />
              <Cifra etiqueta="Plazas instaladas" valor={numero(oferta?.capacidad.total?.plazas)} detalle={`en ${numero(oferta?.capacidad.total?.establecimientos)} alojamientos`} />
              <Cifra etiqueta="Plazas por 100 habitantes" valor={numero(oferta?.plazas_por_100?.valor, 2)}
                detalle={`con ${numero(oferta?.plazas_por_100?.poblacion)} habitantes (proyección INEC)`} />
            </div>

            <div className="grid gap-6 lg:grid-cols-2">
              <figure className="min-w-0 border border-linea bg-papel p-4">
                <figcaption className="font-display text-lg font-semibold">Alojamientos por tipo</figcaption>
                <p className="text-sm text-piedra">Catastro turístico, {mes(oferta?.catastro.corte)}. Los inmuebles habitacionales son viviendas de uso turístico registradas.</p>
                <div className="mt-4 h-72">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={oferta?.catastro.alojamiento_por_clasificacion.map(c => ({ ...c, nombre: titulo(c.clasificacion) }))}
                      layout="vertical" margin={{ top: 0, right: 24, left: 8, bottom: 0 }}>
                      <CartesianGrid stroke="var(--linea)" strokeDasharray="2 4" horizontal={false} />
                      <XAxis type="number" {...ejes} axisLine={false} />
                      <YAxis type="category" dataKey="nombre" {...ejes} axisLine={false} width={150} />
                      <Tooltip contentStyle={tooltip} formatter={v => [numero(Number(v)), 'Establecimientos']} />
                      <Bar dataKey="establecimientos" fill="var(--rojo)" isAnimationActive={false} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </figure>

              <section className="min-w-0 border border-linea bg-papel" aria-labelledby="titulo-capacidad">
                <h3 id="titulo-capacidad" className="border-b border-linea p-4 text-lg">Capacidad instalada por tipo</h3>
                <div className="overflow-x-auto">
                  <table className="tabla min-w-[420px]">
                    <thead><tr><th>Tipo</th><th className="text-right">Alojamientos</th><th className="text-right">Habitaciones</th><th className="text-right">Plazas</th></tr></thead>
                    <tbody>
                      {oferta?.capacidad.por_tipo.map(t => (
                        <tr key={t.tipo}>
                          <td>{titulo(t.tipo)}</td>
                          <td className="numero text-right">{numero(t.establecimientos)}</td>
                          <td className="numero text-right">{numero(t.habitaciones)}</td>
                          <td className="numero text-right">{numero(t.plazas)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>
            </div>

            <section className="border border-linea bg-papel" aria-labelledby="titulo-parroquias">
              <div className="flex flex-wrap items-baseline justify-between gap-2 border-b border-linea p-4">
                <h3 id="titulo-parroquias" className="text-lg">Alojamientos por parroquia</h3>
                <p className="text-sm text-piedra">Catastro turístico, {mes(oferta?.catastro.corte)}.</p>
              </div>
              {/* columnas CSS: el orden de mayor a menor baja por la izquierda y sigue en la derecha */}
              <ul className="gap-x-10 p-4 sm:columns-2">
                {parroquias.map(p => (
                  <li key={p.parroquia} className="grid break-inside-avoid grid-cols-[9rem_1fr_2.5rem] items-center gap-3 py-1.5 text-sm">
                    <span className="truncate" title={p.parroquia}>{p.parroquia}</span>
                    <span className="h-2.5 bg-suave"><span className="block h-full bg-oro" style={{ width: `${p.alojamientos / maxParroquia * 100}%` }} /></span>
                    <span className="numero text-right">{p.alojamientos}</span>
                  </li>
                ))}
              </ul>
            </section>

            <figure className="min-w-0 border border-linea bg-papel p-4">
              <figcaption className="font-display text-lg font-semibold">Todos los establecimientos turísticos por actividad</figcaption>
              <p className="text-sm text-piedra">Catastro turístico, {mes(oferta?.catastro.corte)}.</p>
              <div className="mt-4 h-60">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={oferta?.catastro.por_actividad.map(a => ({ ...a, nombre: titulo(a.actividad) }))}
                    layout="vertical" margin={{ top: 0, right: 24, left: 8, bottom: 0 }}>
                    <CartesianGrid stroke="var(--linea)" strokeDasharray="2 4" horizontal={false} />
                    <XAxis type="number" {...ejes} axisLine={false} />
                    <YAxis type="category" dataKey="nombre" {...ejes} axisLine={false} width={190} />
                    <Tooltip contentStyle={tooltip} formatter={v => [numero(Number(v)), 'Establecimientos']} />
                    <Bar dataKey="establecimientos" fill="var(--oro)" isAnimationActive={false} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </figure>
          </section>

          <section className="grid gap-6 text-sm text-piedra sm:grid-cols-3">
            <p><strong className="text-tinta">Ventas.</strong> SRI, datos abiertos de ventas por cantón y actividad. Revisado el {fecha(economia?.actualizado)}.</p>
            <p><strong className="text-tinta">Oferta.</strong> Catastro turístico nacional (Viceministerio de Turismo) y base municipal de hostelería (Cuenca en Datos). Revisados el {fecha(oferta?.catastro.actualizado)}.</p>
            <p><strong className="text-tinta">Población.</strong> INEC, proyecciones Revisión 2024. Más detalle en <Link to="/metodologia" className="text-rojo underline">Metodología</Link>.</p>
          </section>
        </Estado>
      </main>
      <PiePublico />
    </div>
  )
}
