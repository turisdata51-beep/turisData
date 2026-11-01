import { Fragment, useCallback, useEffect, useRef, useState, type DragEvent } from 'react'
import { Estado } from '../../componentes/Estado'
import { TituloSeccion } from '../../componentes/TituloSeccion'
import { api, descargar } from '../../lib/api'
import { fechaHora } from '../../lib/formato'

type Carga = {
  id: number; nombre_archivo: string; recibido_en: string; estado: string; registros_recibidos: number
  registros_validos: number; registros_rechazados: number; fuente: string; usuario: string | null
  errores: number; advertencias: number
}
type ErrorCarga = { fila: number | null; campo: string | null; valor: string | null; regla: string; mensaje: string; severidad: string }

const ESTADOS: Record<string, { texto: string; clase: string }> = {
  publicada: { texto: 'publicada', clase: 'text-rio' },
  con_errores: { texto: 'parcial', clase: 'text-alerta' },
  rechazada: { texto: 'rechazada', clase: 'text-critico' },
  recibida: { texto: 'recibida', clase: 'text-piedra' },
}

export default function Cargas() {
  const [cargas, setCargas] = useState<Carga[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [subiendo, setSubiendo] = useState(false)
  const [resultado, setResultado] = useState<(Carga & { errores: ErrorCarga[] }) | null>(null)
  const [detalle, setDetalle] = useState<{ id: number; errores: ErrorCarga[] } | null>(null)
  const [arrastrando, setArrastrando] = useState(false)
  const entrada = useRef<HTMLInputElement>(null)

  const refrescar = useCallback(() => api<Carga[]>('/admin/cargas').then(setCargas).catch(e => setError(e.message)), [])
  useEffect(() => { refrescar() }, [refrescar])

  async function subir(archivo: File | undefined) {
    if (!archivo) return
    setSubiendo(true); setResultado(null); setError(null)
    const datos = new FormData()
    datos.append('archivo', archivo)
    try {
      setResultado(await api('/admin/cargas', { method: 'POST', body: datos }))
      refrescar()
    } catch (e) { setError((e as Error).message) } finally {
      setSubiendo(false)
      if (entrada.current) entrada.current.value = ''
    }
  }

  async function verErrores(id: number) {
    if (detalle?.id === id) { setDetalle(null); return }
    setDetalle({ id, errores: await api<ErrorCarga[]>(`/admin/cargas/${id}/errores`) })
  }

  function soltar(e: DragEvent) {
    e.preventDefault(); setArrastrando(false)
    subir(e.dataTransfer.files[0])
  }

  return (
    <>
      <TituloSeccion titulo="Cargas de datos" descripcion="Suba el reporte mensual de alojamiento con la plantilla oficial. Las filas con errores se rechazan y las demás se publican.">
        <button type="button" className="boton-sec" onClick={() => descargar('/admin/plantilla', 'reporte_mensual_alojamiento_v1.xlsx')}>Descargar plantilla</button>
      </TituloSeccion>

      <label htmlFor="archivo"
        onDragOver={e => { e.preventDefault(); setArrastrando(true) }} onDragLeave={() => setArrastrando(false)} onDrop={soltar}
        className={`flex cursor-pointer flex-col items-center gap-2 border-2 border-dashed p-8 text-center transition-colors ${arrastrando ? 'border-rojo bg-rojo-suave' : 'border-linea bg-papel hover:border-rojo'}`}>
        <span className="font-display text-xl">{subiendo ? 'Validando el archivo…' : 'Arrastre aquí el archivo o haga clic para elegirlo'}</span>
        <span className="text-sm text-piedra">Archivos .xlsx o .csv de hasta 5 MB, con la plantilla v1</span>
        <input ref={entrada} id="archivo" type="file" accept=".xlsx,.csv" className="sr-only" disabled={subiendo} onChange={e => subir(e.target.files?.[0])} />
      </label>

      {error && <p className="border border-critico/40 bg-papel p-3 text-critico" role="alert">{error}</p>}

      {resultado && (
        <section className={`border bg-papel p-4 ${resultado.estado === 'rechazada' ? 'border-critico' : resultado.estado === 'con_errores' ? 'border-alerta' : 'border-rio'}`} aria-live="polite">
          <p className="font-semibold">
            Carga #{resultado.id}: {resultado.registros_validos} de {resultado.registros_recibidos} filas publicadas
            <span className={`ml-2 pastilla ${ESTADOS[resultado.estado]?.clase}`}>{ESTADOS[resultado.estado]?.texto}</span>
          </p>
          {resultado.errores.length > 0 && <ListaErrores errores={resultado.errores} />}
        </section>
      )}

      <Estado cargando={!cargas && !error} error={null}>
        <section className="border border-linea bg-papel">
          <h2 className="border-b border-linea p-4 text-xl">Historial</h2>
          <div className="overflow-x-auto">
            <table className="tabla min-w-[720px]">
              <thead><tr><th>#</th><th>Archivo</th><th>Recibido</th><th>Por</th><th className="text-right">Filas</th><th>Estado</th><th></th></tr></thead>
              <tbody>
                {cargas?.map(c => (
                  <Fragment key={c.id}>
                    <tr>
                      <td className="numero">{c.id}</td>
                      <td className="max-w-[16rem] break-words">{c.nombre_archivo}</td>
                      <td className="whitespace-nowrap">{fechaHora(c.recibido_en)}</td>
                      <td className="text-piedra">{c.usuario ?? 'carga automática'}</td>
                      <td className="numero whitespace-nowrap text-right">{c.registros_validos}/{c.registros_recibidos}</td>
                      <td><span className={`pastilla ${ESTADOS[c.estado]?.clase}`}>{ESTADOS[c.estado]?.texto ?? c.estado}</span></td>
                      <td className="text-right">
                        {c.errores + c.advertencias > 0 && (
                          <button type="button" className="text-sm font-semibold text-rojo" onClick={() => verErrores(c.id)}>
                            {detalle?.id === c.id ? 'Ocultar' : `Ver ${c.errores + c.advertencias} observaciones`}
                          </button>
                        )}
                      </td>
                    </tr>
                    {detalle?.id === c.id && (
                      <tr><td colSpan={7} className="bg-suave"><ListaErrores errores={detalle.errores} /></td></tr>
                    )}
                  </Fragment>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </Estado>
    </>
  )
}

function ListaErrores({ errores }: { errores: ErrorCarga[] }) {
  return (
    <ul className="mt-3 space-y-1 text-sm">
      {errores.map((e, i) => (
        <li key={i} className="flex flex-wrap gap-x-2">
          <span className={`font-semibold ${e.severidad === 'error' ? 'text-critico' : 'text-alerta'}`}>{e.fila ? `Fila ${e.fila}` : 'Archivo'}</span>
          {e.campo && <code className="numero text-piedra">{e.campo}</code>}
          <span>{e.mensaje}</span>
        </li>
      ))}
    </ul>
  )
}
