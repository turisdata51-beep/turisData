import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { EncabezadoPublico } from '../../componentes/EncabezadoPublico'
import { TarjetaKpi } from '../../componentes/Indicador'
import { PiePublico } from '../../componentes/PiePublico'
import { api } from '../../lib/api'
import { mes, numero, valorKpi } from '../../lib/formato'
import type { Contenido, Kpi, Resumen } from '../../lib/tipos'

type Punto = { periodo: string; B4?: number }

const CLASE_FRASE = 'max-w-[34ch] text-[clamp(1.2rem,2vw,1.5rem)] leading-snug text-tinta'
const FRASE_RESERVA = 'En septiembre 2026, los 26 alojamientos que reportan vendieron el 55,8 % de sus habitaciones y sumaron 23.732 pernoctaciones, 4,2 % más que en septiembre 2025.'
const SUBTITULO_RESERVA = 'Datos confiables y comparables sobre el turismo de Cuenca para que el sector tome mejores decisiones.'
const AVISO_RESERVA = 'Las cifras actuales son datos de demostración generados para el prototipo; no representan a establecimientos reales.'

/** La frase de portada: el mes contado con sus propias cifras. */
function FraseDelMes({ resumen }: { resumen: Resumen }) {
  const k = (c: string) => resumen.kpis.find(x => x.codigo === c) as Kpi | undefined
  const ocupacion = k('B4'), noches = k('A2')
  if (!ocupacion?.valor || !noches?.valor) return null
  const anterior = resumen.periodo ? mes(`${Number(resumen.periodo.slice(0, 4)) - 1}${resumen.periodo.slice(4)}`) : ''
  const cambio = noches.variacion_interanual
  return (
    <p className={CLASE_FRASE}>
      En {mes(resumen.periodo)}, los {ocupacion.n_unidades} alojamientos que reportan vendieron
      el {valorKpi(ocupacion.valor, '%')} de sus habitaciones y sumaron {numero(noches.valor)} pernoctaciones
      {cambio !== null && <>, {numero(Math.abs(cambio), 1)}{' '}% {cambio >= 0 ? 'más' : 'menos'} que en {anterior}</>}.
    </p>
  )
}

export default function Inicio() {
  const [c, setC] = useState<Contenido | null>(null)
  const [resumen, setResumen] = useState<Resumen | null>(null)
  const [serie, setSerie] = useState<Punto[]>([])

  useEffect(() => {
    api<Contenido>('/public/contenido').then(setC).catch(() => setC(null))
    api<Resumen>('/public/resumen').then(setResumen).catch(() => setResumen(null))
    api<Punto[]>('/public/series?codigos=B4').then(s => setSerie(s.slice(-24))).catch(() => setSerie([]))
  }, [])

  // La frase ya cuenta ocupación y pernoctaciones; la pared muestra las otras tres cifras clave
  const pared = (resumen?.kpis ?? []).filter(k => ['A1', 'A4', 'B6'].includes(k.codigo))

  return (
    <div className="min-h-screen bg-fondo">
      <EncabezadoPublico />

      {/* Portada: título y frase del mes a la izquierda, logo a la derecha; debajo, tres cifras clave */}
      <section>
        <div className="marco grid items-center gap-10 pt-14 pb-10 lg:grid-cols-[1.35fr_1fr] lg:pt-20">
          <div className="flex min-w-0 flex-col justify-center gap-7">
            <h1 className="text-[clamp(2.2rem,4.8vw,3.8rem)] text-tinta">
              {c?.hero_titulo ?? 'Observatorio Turístico Inteligente de Cuenca'}
            </h1>
            {resumen ? <FraseDelMes resumen={resumen} /> : (
              // Mientras llegan los datos, una frase invisible del mismo largo reserva el espacio y nada se mueve
              <p aria-hidden className={`invisible ${CLASE_FRASE}`}>{FRASE_RESERVA}</p>
            )}
            <p className={`max-w-[52ch] text-piedra ${c ? '' : 'invisible'}`}>{c?.hero_subtitulo ?? SUBTITULO_RESERVA}</p>
            <div className="flex flex-wrap gap-3">
              <Link to="/observatorio" className="boton">Ver todos los indicadores</Link>
              <a href="#camara" className="boton-sec">Conocer la Cámara</a>
            </div>
            {(!c || c.aviso_datos) && (
              <p className={`max-w-[60ch] border-l-2 border-alerta pl-3 text-sm text-piedra ${c ? '' : 'invisible'}`}>{c?.aviso_datos ?? AVISO_RESERVA}</p>
            )}
          </div>

          <img src="/logo-web.webp" alt="Logo de TurisData Azuay - Cuenca: pin con la Catedral, el puente y el río Tomebamba junto a un gráfico de barras"
            className="mx-auto hidden w-full max-w-[420px] lg:block" width={720} height={706} />
        </div>
        <div className="marco pb-16">
          <div className="lechada sm:grid-cols-3">
            {pared.length ? pared.map(k => <TarjetaKpi key={k.codigo} kpi={k} />) : (
              <p className="p-5 text-piedra">Todavía no hay cifras publicadas.</p>
            )}
          </div>
        </div>
      </section>

      {/* La Cámara */}
      <section id="camara" className="marco grid gap-10 py-16 lg:grid-cols-[1fr_1.4fr]">
        <h2 className="min-w-0 text-[clamp(1.8rem,3.4vw,2.6rem)]">{c?.camara_nombre ?? 'Cámara de Turismo del Azuay'}</h2>
        <div className="min-w-0 space-y-8">
          <p className="max-w-[65ch] text-lg">{c?.camara_descripcion}</p>
          <div className="grid gap-6 sm:grid-cols-2">
            <div className="border-t border-linea pt-4">
              <h3 className="font-texto text-base font-semibold">Misión</h3>
              <p className="mt-2 text-piedra">{c?.mision}</p>
            </div>
            <div className="border-t border-linea pt-4">
              <h3 className="font-texto text-base font-semibold">Visión</h3>
              <p className="mt-2 text-piedra">{c?.vision}</p>
            </div>
          </div>
        </div>
      </section>

      <div className="marco"><hr className="border-linea" /></div>

      {/* Servicios */}
      <section className="marco py-16">
        <h2 className="text-[clamp(1.7rem,3vw,2.3rem)]">Qué hace la Cámara por el sector</h2>
        <ul className="mt-8 grid gap-x-10 sm:grid-cols-2">
          {(c?.servicios ?? []).map(s => (
            <li key={s.titulo} className="grid grid-cols-[auto_1fr] gap-4 border-t border-linea py-5">
              <span className="mt-2.5 block h-[3px] w-4 bg-oro" aria-hidden />
              <div className="min-w-0">
                <h3 className="text-xl">{s.titulo}</h3>
                <p className="mt-1 text-piedra">{s.texto}</p>
              </div>
            </li>
          ))}
        </ul>
      </section>

      {/* Destino + adelanto del observatorio */}
      <section className="border-y border-linea bg-suave">
        <div className="marco grid gap-10 py-16 lg:grid-cols-[1fr_1.2fr]">
          <div className="min-w-0">
            <h2 className="text-[clamp(1.7rem,3vw,2.3rem)]">{c?.destino_titulo}</h2>
            <p className="mt-4 max-w-[60ch]">{c?.destino_texto}</p>
            <p className="mt-6 max-w-[60ch] text-piedra">
              El observatorio reúne cada mes los reportes de los alojamientos asociados y calcula
              llegadas, pernoctaciones, ocupación y tarifa media con metodologías internacionales.
            </p>
            <Link to="/observatorio" className="boton mt-6">Abrir el observatorio</Link>
          </div>
          <figure className="min-w-0 border border-linea bg-papel p-5">
            <figcaption>
              <span className="block font-display text-lg font-semibold">Ocupación de habitaciones en los últimos 24 meses</span>
              <span className="text-sm text-piedra">Porcentaje de habitaciones vendidas en el cantón Cuenca</span>
            </figcaption>
            <div className="mt-4 h-56">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={serie} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
                  <defs>
                    <linearGradient id="relleno-ocupacion" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="var(--rojo)" stopOpacity={0.28} />
                      <stop offset="100%" stopColor="var(--rojo)" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <XAxis dataKey="periodo" tickFormatter={p => mes(p, true)} tick={{ fill: 'var(--piedra)', fontSize: 11 }} axisLine={{ stroke: 'var(--linea)' }} tickLine={false} minTickGap={24} />
                  <YAxis domain={[30, 80]} ticks={[30, 40, 50, 60, 70, 80]} tick={{ fill: 'var(--piedra)', fontSize: 11 }} axisLine={false} tickLine={false} />
                  <Tooltip formatter={v => [`${numero(Number(v), 1)} %`, 'Ocupación']} labelFormatter={p => mes(String(p))}
                    contentStyle={{ background: 'var(--papel)', border: '1px solid var(--linea)', color: 'var(--tinta)' }} />
                  <Area type="monotone" isAnimationActive={false} dataKey="B4" stroke="var(--rojo)" strokeWidth={2} fill="url(#relleno-ocupacion)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </figure>
        </div>
      </section>

      <PiePublico />
    </div>
  )
}
