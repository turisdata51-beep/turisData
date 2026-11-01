// Panel: edición de los textos de la página de inicio.
import { useEffect, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { Estado } from '../../componentes/Estado'
import { TituloSeccion } from '../../componentes/TituloSeccion'
import { api } from '../../lib/api'
import type { Contenido } from '../../lib/tipos'

const CAMPOS_CONTENIDO: { clave: keyof Contenido; etiqueta: string; largo?: boolean }[] = [
  { clave: 'hero_titulo', etiqueta: 'Título principal' },
  { clave: 'hero_subtitulo', etiqueta: 'Subtítulo', largo: true },
  { clave: 'camara_nombre', etiqueta: 'Nombre de la institución' },
  { clave: 'camara_descripcion', etiqueta: 'Quiénes somos', largo: true },
  { clave: 'mision', etiqueta: 'Misión', largo: true },
  { clave: 'vision', etiqueta: 'Visión', largo: true },
  { clave: 'destino_titulo', etiqueta: 'Título del destino' },
  { clave: 'destino_texto', etiqueta: 'Texto del destino', largo: true },
  { clave: 'contacto_direccion', etiqueta: 'Dirección' },
  { clave: 'contacto_telefono', etiqueta: 'Teléfono' },
  { clave: 'contacto_correo', etiqueta: 'Correo de contacto' },
  { clave: 'contacto_web', etiqueta: 'Sitio web' },
  { clave: 'aviso_datos', etiqueta: 'Aviso sobre los datos (dejar vacío para ocultarlo)', largo: true },
]

export default function ContenidoSitio() {
  const [c, setC] = useState<Contenido | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [guardado, setGuardado] = useState(false)
  useEffect(() => { api<Contenido>('/admin/contenido').then(setC).catch(e => setError(e.message)) }, [])

  async function guardar(e: FormEvent) {
    e.preventDefault(); setGuardado(false); setError(null)
    try { setC(await api<Contenido>('/admin/contenido', { method: 'PUT', body: JSON.stringify(c) })); setGuardado(true) }
    catch (err) { setError((err as Error).message) }
  }
  const servicio = (i: number, k: 'titulo' | 'texto', v: string) =>
    setC(x => x && { ...x, servicios: x.servicios.map((s, j) => j === i ? { ...s, [k]: v } : s) })

  return (
    <>
      <TituloSeccion titulo="Contenido del sitio" descripcion="Textos de la página de inicio. Los cambios se publican al guardar.">
        <Link to="/" target="_blank" className="boton-sec">Ver página de inicio</Link>
      </TituloSeccion>
      <Estado cargando={!c && !error} error={error}>
        {c && (
          <form onSubmit={guardar} className="space-y-6">
            <div className="grid gap-4 border border-linea bg-papel p-5 md:grid-cols-2">
              {CAMPOS_CONTENIDO.map(f => (
                <label key={f.clave} htmlFor={`c-${f.clave}`} className={`grid gap-1 text-sm ${f.largo ? 'md:col-span-2' : ''}`}>
                  <span className="font-semibold">{f.etiqueta}</span>
                  {f.largo
                    ? <textarea id={`c-${f.clave}`} rows={3} className="campo" value={String(c[f.clave] ?? '')} onChange={e => setC({ ...c, [f.clave]: e.target.value })} />
                    : <input id={`c-${f.clave}`} className="campo" value={String(c[f.clave] ?? '')} onChange={e => setC({ ...c, [f.clave]: e.target.value })} />}
                </label>
              ))}
            </div>
            <fieldset className="grid gap-4 border border-linea bg-papel p-5 md:grid-cols-2">
              <legend className="px-1 font-display text-lg font-semibold">Servicios</legend>
              {c.servicios.map((s, i) => (
                <div key={i} className="grid gap-2">
                  <input id={`s-titulo-${i}`} aria-label={`Título del servicio ${i + 1}`} className="campo font-semibold" value={s.titulo} onChange={e => servicio(i, 'titulo', e.target.value)} />
                  <textarea id={`s-texto-${i}`} aria-label={`Descripción del servicio ${i + 1}`} rows={2} className="campo" value={s.texto} onChange={e => servicio(i, 'texto', e.target.value)} />
                </div>
              ))}
            </fieldset>
            <div className="flex items-center gap-3">
              <button className="boton">Guardar cambios</button>
              {guardado && <span className="text-rio" role="status">Cambios publicados</span>}
            </div>
          </form>
        )}
      </Estado>
    </>
  )
}
