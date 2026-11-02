import { Fragment, useCallback, useEffect, useRef, useState, type DragEvent } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Estado } from '../../componentes/Estado'
import { TituloSeccion } from '../../componentes/TituloSeccion'
import { api, descargar } from '../../lib/api'
import { fechaHora } from '../../lib/formato'

type Plantilla = {
  codigo: string; nombre: string; descripcion: string; unidad: string; version: string
  columnas: { nombre: string; tipo: string; obligatoria: boolean; descripcion: string }[]
}
type Carga = {
  id: number; nombre_archivo: string; recibido_en: string; estado: string; plantilla_nombre: string; registros_recibidos: number
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
  const [parametros, setParametros] = useSearchParams()
  const [plantillas, setPlantillas] = useState<Plantilla[]>([])
  const [verColumnas, setVerColumnas] = useState(false)
  const [cargas, setCargas] = useState<Carga[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [subiendo, setSubiendo] = useState(false)
  const [resultado, setResultado] = useState<(Carga & { errores: ErrorCarga[] }) | null>(null)
  const [detalle, setDetalle] = useState<{ id: number; errores: ErrorCarga[] } | null>(null)
  const [arrastrando, setArrastrando] = useState(false)
  const entrada = useRef<HTMLInputElement>(null)

  const refrescar = useCallback(() => api<Carga[]>('/admin/cargas').then(setCargas).catch(e => setError(e.message)), [])
  useEffect(() => { refrescar() }, [refrescar])
  useEffect(() => { api<Plantilla[]>('/admin/plantillas').then(setPlantillas).catch(e => setError(e.message)) }, [])

  // La plantilla elegida queda en la dirección (?plantilla=empleo) para volver directo a ella
  const plantilla = plantillas.find(p => p.codigo === parametros.get('plantilla')) ?? plantillas[0]
  function elegir(codigo: string) {
    setParametros({ plantilla: codigo }, { replace: true })
    setResultado(null); setVerColumnas(false)
  }

  async function subir(archivo: File | undefined) {
    if (!archivo) return
    setSubiendo(true); setResultado(null); setError(null)
    const datos = new FormData()
    datos.append('archivo', archivo)
    datos.append('plantilla', plantilla?.codigo ?? 'alojamiento')
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
      <TituloSeccion titulo="Cargas de datos" descripcion="Elija qué va a reportar, descargue su plantilla y súbala llena. Las filas con errores se rechazan y las demás se publican." />

      <div role="radiogroup" aria-label="Tipo de reporte" className="flex flex-wrap gap-2">
        {plantillas.map(p => (
          <button key={p.codigo} type="button" role="radio" aria-checked={p.codigo === plantilla?.codigo} onClick={() => elegir(p.codigo)}
            className={`rounded-md border px-3 py-2 text-sm font-semibold ${p.codigo === plantilla?.codigo ? 'border-rojo bg-rojo-suave text-rojo' : 'border-linea bg-papel hover:border-tinta'}`}>
            {p.nombre}
          </button>
        ))}
      </div>

      {plantilla && (
        <section className="space-y-3 border border-linea bg-papel p-4" aria-live="polite">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0">
              <h2 className="text-lg">{plantilla.nombre}</h2>
              <p className="max-w-[70ch] text-sm text-piedra">{plantilla.descripcion} Una fila por {plantilla.unidad}.</p>
            </div>
            <div className="flex flex-wrap gap-2">
              <button type="button" className="boton-sec !py-1.5 text-sm"
                onClick={() => descargar(`/admin/plantillas/${plantilla.codigo}.xlsx`, `plantilla_${plantilla.codigo}_${plantilla.version}.xlsx`)}>
                Descargar Excel
              </button>
              <button type="button" className="boton-sec !py-1.5 text-sm"
                onClick={() => descargar(`/admin/plantillas/${plantilla.codigo}.csv`, `plantilla_${plantilla.codigo}_${plantilla.version}.csv`)}>
                CSV
              </button>
            </div>
          </div>
          <button type="button" className="text-sm font-semibold text-rojo" aria-expanded={verColumnas} onClick={() => setVerColumnas(v => !v)}>
            {verColumnas ? 'Ocultar columnas' : `Ver sus ${plantilla.columnas.length} columnas`}
          </button>
          {verColumnas && (
            <div className="overflow-x-auto">
              <table className="tabla min-w-[560px]">
                <thead><tr><th>Columna</th><th>Qué poner</th></tr></thead>
                <tbody>
                  {plantilla.columnas.map(c => (
                    <tr key={c.nombre}>
                      <td className="whitespace-nowrap font-semibold">{c.nombre}{!c.obligatoria && <span className="ml-1 font-normal text-piedra">(opcional)</span>}</td>
                      <td className="text-piedra">{c.descripcion.replace(/^OPCIONAL\. /, '')}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}

      <label htmlFor="archivo"
        onDragOver={e => { e.preventDefault(); setArrastrando(true) }} onDragLeave={() => setArrastrando(false)} onDrop={soltar}
        className={`flex cursor-pointer flex-col items-center gap-2 border-2 border-dashed p-8 text-center transition-colors ${arrastrando ? 'border-rojo bg-rojo-suave' : 'border-linea bg-papel hover:border-rojo'}`}>
        <span className="font-display text-xl">{subiendo ? 'Validando el archivo…' : 'Arrastre aquí el archivo o haga clic para elegirlo'}</span>
        <span className="text-sm text-piedra">{plantilla ? `${plantilla.nombre}: ` : ''}archivo .xlsx o .csv de hasta 5 MB</span>
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
            <table className="tabla min-w-[860px]">
              <thead><tr><th>#</th><th>Tipo</th><th>Archivo</th><th>Recibido</th><th>Por</th><th className="text-right">Filas</th><th>Estado</th><th></th></tr></thead>
              <tbody>
                {cargas?.map(c => (
                  <Fragment key={c.id}>
                    <tr>
                      <td className="numero">{c.id}</td>
                      <td className="text-piedra">{c.plantilla_nombre}</td>
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
                      <tr><td colSpan={8} className="bg-suave"><ListaErrores errores={detalle.errores} /></td></tr>
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
