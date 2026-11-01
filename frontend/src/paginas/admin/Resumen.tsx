import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Estado } from '../../componentes/Estado'
import { Placa } from '../../componentes/Indicador'
import { TituloSeccion } from '../../componentes/TituloSeccion'
import { api, descargar } from '../../lib/api'
import { fechaHora, mes, numero } from '../../lib/formato'
import { useSesion } from '../../sesion/sesion'

type Datos = {
  q1_cobertura: { periodo: string; valor: number } | null
  q2_completitud: number | null
  q3_frescura: { codigo: string; nombre: string; sla_dias: number | null; prioritaria: boolean; ultima_carga: string | null; dias: number | null }[]
  q4_fuentes_al_dia: number | null
  q5_registros_validos: number | null
  conteos: { establecimientos: number; usuarios: number; cargas: number; reportes: number }
  metas: Record<string, string>
}

function estado(valor: number | null, meta: number) {
  if (valor === null) return { texto: 'sin datos', clase: 'text-piedra' }
  if (valor >= meta) return { texto: 'cumple', clase: 'text-rio' }
  if (valor >= meta * 0.8) return { texto: 'atención', clase: 'text-alerta' }
  return { texto: 'crítico', clase: 'text-critico' }
}

function Control({ codigo, nombre, valor, meta, detalle }: { codigo: string; nombre: string; valor: number | null; meta: number; detalle: string }) {
  const e = estado(valor, meta)
  return (
    <article className="flex flex-col gap-2 p-5">
      <div className="flex items-center justify-between gap-2"><Placa codigo={codigo} /><span className={`pastilla ${e.clase}`}>{e.texto}</span></div>
      <h3 className="font-texto text-sm font-semibold text-piedra">{nombre}</h3>
      <p className="cifra text-[2.2rem]">{valor === null ? '—' : `${numero(valor, 1)} %`}</p>
      <div className="h-1 bg-suave" aria-hidden><div className="h-full bg-oro" style={{ width: `${Math.min(valor ?? 0, 100)}%` }} /></div>
      <p className="text-sm text-piedra">Meta: {meta} % o más, {detalle}</p>
    </article>
  )
}

export default function Resumen() {
  const { usuario } = useSesion()
  const [d, setD] = useState<Datos | null>(null)
  const [error, setError] = useState<string | null>(null)
  useEffect(() => { api<Datos>('/admin/resumen').then(setD).catch(e => setError(e.message)) }, [])

  return (
    <>
      <TituloSeccion titulo={`Hola, ${usuario?.nombre.split(' ')[0]}`} descripcion="Estado de las fuentes y de la calidad de los datos del observatorio.">
        <button type="button" className="boton-sec" onClick={() => descargar('/admin/exportar', 'observatorio_indicadores.csv')}>Exportar indicadores (CSV)</button>
        {usuario?.rol !== 'consulta' && <Link to="/admin/cargas" className="boton">Cargar reporte</Link>}
      </TituloSeccion>
      <Estado cargando={!d && !error} error={error}>
        {d && (
          <>
            <section className="lechada sm:grid-cols-2 lg:grid-cols-4" aria-label="Controles de calidad">
              <Control codigo="Q1" nombre="Establecimientos que reportaron" valor={d.q1_cobertura?.valor ?? null} meta={90} detalle={mes(d.q1_cobertura?.periodo)} />
              <Control codigo="Q2" nombre="Campos obligatorios completos" valor={d.q2_completitud} meta={95} detalle="en la última carga" />
              <Control codigo="Q4" nombre="Fuentes prioritarias al día" valor={d.q4_fuentes_al_dia} meta={Number(d.metas.meta_fuentes_al_dia_pct)} detalle="según el plazo de cada fuente" />
              <Control codigo="Q5" nombre="Registros válidos" valor={d.q5_registros_validos} meta={Number(d.metas.meta_registros_validos_pct)} detalle="en la última carga" />
            </section>

            <section className="grid gap-6 lg:grid-cols-[1.5fr_1fr]">
              <div className="min-w-0 border border-linea bg-papel">
                <div className="flex items-center gap-2 border-b border-linea p-4"><Placa codigo="Q3" /><h2 className="text-xl">Frescura de las fuentes</h2></div>
                <div className="overflow-x-auto">
                  <table className="tabla">
                    <thead><tr><th>Fuente</th><th>Última carga</th><th className="text-right">Días</th><th>Plazo</th></tr></thead>
                    <tbody>
                      {d.q3_frescura.map(f => {
                        const vencida = f.dias !== null && f.sla_dias !== null && f.dias > f.sla_dias
                        return (
                          <tr key={f.codigo}>
                            <td>{f.nombre}{f.prioritaria && <span className="ml-2 pastilla text-rojo">prioritaria</span>}</td>
                            <td className="whitespace-nowrap">{fechaHora(f.ultima_carga)}</td>
                            <td className={`numero text-right ${vencida ? 'text-critico' : ''}`}>{f.dias === null ? '—' : numero(f.dias, 0)}</td>
                            <td className="whitespace-nowrap text-piedra">{f.sla_dias ? `${f.sla_dias} días` : '—'}</td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
              <dl className="grid grid-cols-2 gap-px self-start border border-linea bg-linea">
                {[
                  ['Establecimientos activos', d.conteos.establecimientos],
                  ['Reportes vigentes', d.conteos.reportes],
                  ['Cargas registradas', d.conteos.cargas],
                  ['Usuarios activos', d.conteos.usuarios],
                ].map(([t, v]) => (
                  <div key={t} className="bg-papel p-4">
                    <dt className="text-xs text-piedra">{t}</dt>
                    <dd className="cifra mt-2 text-2xl">{numero(Number(v))}</dd>
                  </div>
                ))}
              </dl>
            </section>
          </>
        )}
      </Estado>
    </>
  )
}
