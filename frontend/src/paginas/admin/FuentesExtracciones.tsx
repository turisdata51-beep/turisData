// Panel: fuentes de datos, estado de las extracciones automáticas y ejecución manual (RF-02, RF-04).
import { Fragment, useCallback, useEffect, useState } from 'react'
import { Estado } from '../../componentes/Estado'
import { TituloSeccion } from '../../componentes/TituloSeccion'
import { api } from '../../lib/api'
import { fecha, fechaHora, numero } from '../../lib/formato'
import { useSesion } from '../../sesion/sesion'

type Fuente = {
  codigo: string; nombre: string; entidad_propietaria: string; tipo_fuente: string; formato: string
  cobertura_geografica: string | null; extractor: string | null; frecuencia_extraccion_dias: number | null
  activa: boolean; observaciones: string | null
  ultimo_estado: string | null; ultima_ejecucion: string | null; ultimo_mensaje: string | null
  registros_nuevos: number | null; registros_actualizados: number | null
  ultima_correcta: string | null; proxima_revision: string | null; datos_vigentes: number
  ultima_carga_manual: string | null
}
type Ejecucion = {
  id: number; iniciada_en: string; terminada_en: string | null; estado: string
  registros_nuevos: number; registros_actualizados: number; mensaje: string | null; usuario: string | null
}

const ESTADOS: Record<string, { texto: string; clase: string }> = {
  ok: { texto: 'actualizada', clase: 'text-rio' },
  sin_cambios: { texto: 'sin cambios', clase: 'text-piedra' },
  error: { texto: 'con error', clase: 'text-critico' },
  en_curso: { texto: 'extrayendo…', clase: 'text-alerta' },
}
const FRECUENCIAS = [1, 7, 15, 30, 60, 90, 180]

function PastillaEstado({ estado }: { estado: string | null }) {
  if (!estado) return <span className="pastilla text-piedra">nunca ejecutada</span>
  const e = ESTADOS[estado] ?? { texto: estado, clase: 'text-piedra' }
  return <span className={`pastilla ${e.clase}`}>{e.texto}</span>
}

export default function FuentesExtracciones() {
  const { usuario } = useSesion()
  const [fuentes, setFuentes] = useState<Fuente[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [aviso, setAviso] = useState<string | null>(null)
  const [historial, setHistorial] = useState<{ codigo: string; filas: Ejecucion[] } | null>(null)

  const puedeEjecutar = usuario?.rol === 'administrador' || usuario?.rol === 'analista'
  const esAdmin = usuario?.rol === 'administrador'

  const refrescar = useCallback(() => api<Fuente[]>('/admin/fuentes').then(setFuentes).catch(e => setError(e.message)), [])
  useEffect(() => { refrescar() }, [refrescar])

  // Mientras alguna extracción está en curso, se actualiza sola cada 4 segundos
  const enCurso = fuentes?.some(f => f.ultimo_estado === 'en_curso') ?? false
  useEffect(() => {
    if (!enCurso) return
    const id = window.setInterval(refrescar, 4000)
    return () => window.clearInterval(id)
  }, [enCurso, refrescar])

  async function ejecutar(f: Fuente) {
    setAviso(null); setError(null)
    try {
      await api(`/admin/fuentes/${f.codigo}/ejecutar`, { method: 'POST' })
      setAviso(`Extracción de "${f.nombre}" iniciada. Puede tardar unos minutos por la pausa que exige cada sitio.`)
      window.setTimeout(refrescar, 800)
    } catch (e) { setError((e as Error).message) }
  }

  async function cambiarFrecuencia(f: Fuente, dias: number) {
    try {
      await api(`/admin/fuentes/${f.codigo}`, { method: 'PATCH', body: JSON.stringify({ frecuencia_extraccion_dias: dias }) })
      refrescar()
    } catch (e) { setError((e as Error).message) }
  }

  async function verHistorial(f: Fuente) {
    if (historial?.codigo === f.codigo) { setHistorial(null); return }
    setHistorial({ codigo: f.codigo, filas: await api<Ejecucion[]>(`/admin/fuentes/${f.codigo}/ejecuciones`) })
  }

  const automaticas = fuentes?.filter(f => f.extractor) ?? []
  const manuales = fuentes?.filter(f => !f.extractor) ?? []

  return (
    <>
      <TituloSeccion titulo="Fuentes y extracciones"
        descripcion="Las fuentes automáticas se revisan solas según su frecuencia; si la fuente publicó algo nuevo, se guarda y los indicadores se recalculan. Las manuales dependen de que alguien suba el archivo." />
      {aviso && <p className="border border-rio/40 bg-papel p-3 text-sm text-rio" role="status">{aviso}</p>}

      <Estado cargando={!fuentes && !error} error={error}>
        <section aria-labelledby="titulo-automaticas" className="space-y-3">
          <h2 id="titulo-automaticas" className="text-xl">Automáticas (scraping y descargas)</h2>
          <div className="overflow-x-auto border border-linea bg-papel">
            <table className="tabla min-w-[820px]">
              <thead>
                <tr><th>Fuente</th><th>Estado</th><th>Actualizada</th><th>Próxima revisión</th><th>Frecuencia</th><th className="text-right">Datos</th><th></th></tr>
              </thead>
              <tbody>
                {automaticas.map(f => (
                  <Fragment key={f.codigo}>
                    <tr>
                      <td className="min-w-[15rem]">
                        <p className="font-semibold">{f.nombre}</p>
                        <p className="text-xs text-piedra">{f.entidad_propietaria}</p>
                        {f.ultimo_estado === 'error' && <p className="mt-1 text-xs text-critico">{f.ultimo_mensaje}</p>}
                      </td>
                      <td><PastillaEstado estado={f.ultimo_estado} /></td>
                      <td className="whitespace-nowrap" title={fechaHora(f.ultima_correcta)}>{fecha(f.ultima_correcta)}</td>
                      <td className="whitespace-nowrap text-piedra" title={fechaHora(f.proxima_revision)}>{f.activa ? fecha(f.proxima_revision) : 'desactivada'}</td>
                      <td>
                        {esAdmin ? (
                          <select id={`frecuencia-${f.codigo}`} aria-label={`Frecuencia de ${f.nombre}`} className="campo !w-auto !py-1 !text-sm"
                            value={f.frecuencia_extraccion_dias ?? ''} onChange={e => cambiarFrecuencia(f, Number(e.target.value))}>
                            {FRECUENCIAS.map(d => <option key={d} value={d}>cada {d} {d === 1 ? 'día' : 'días'}</option>)}
                          </select>
                        ) : <span className="text-piedra">cada {f.frecuencia_extraccion_dias} días</span>}
                      </td>
                      <td className="numero text-right">{numero(f.datos_vigentes)}</td>
                      <td className="whitespace-nowrap text-right">
                        <div className="flex flex-col items-end gap-2">
                          <button type="button" className="text-sm font-semibold text-rojo" onClick={() => verHistorial(f)}>
                            {historial?.codigo === f.codigo ? 'Ocultar historial' : 'Historial'}
                          </button>
                          {puedeEjecutar && (
                            <button type="button" className="boton !px-3 !py-1.5 text-sm" disabled={f.ultimo_estado === 'en_curso'} onClick={() => ejecutar(f)}>
                              {f.ultimo_estado === 'en_curso' ? 'Extrayendo…' : 'Ejecutar ahora'}
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                    {historial?.codigo === f.codigo && (
                      <tr>
                        <td colSpan={7} className="bg-suave">
                          <ul className="space-y-1 text-sm">
                            {historial.filas.map(e => (
                              <li key={e.id} className="flex flex-wrap items-baseline gap-x-3">
                                <span className="whitespace-nowrap">{fechaHora(e.iniciada_en)}</span>
                                <PastillaEstado estado={e.estado} />
                                <span className="text-piedra">
                                  {e.estado === 'ok' ? `${e.registros_nuevos} nuevos, ${e.registros_actualizados} corregidos` : e.mensaje}
                                  {e.usuario ? `, lanzada por ${e.usuario}` : ', programada o desde la terminal'}
                                </span>
                              </li>
                            ))}
                          </ul>
                        </td>
                      </tr>
                    )}
                  </Fragment>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section aria-labelledby="titulo-manuales" className="space-y-3">
          <h2 id="titulo-manuales" className="text-xl">Manuales (carga de archivos)</h2>
          <ul className="divide-y divide-linea border border-linea bg-papel">
            {manuales.map(f => (
              <li key={f.codigo} className="flex flex-wrap items-baseline justify-between gap-2 p-4">
                <div className="min-w-0">
                  <p className="font-semibold">{f.nombre}</p>
                  <p className="text-xs text-piedra">{f.entidad_propietaria}</p>
                </div>
                <p className="text-sm text-piedra">Última carga: {fechaHora(f.ultima_carga_manual)}</p>
              </li>
            ))}
          </ul>
        </section>
      </Estado>
    </>
  )
}
