// Secciones más simples del panel: indicadores, contenido del sitio, auditoría y reportes del asociado.
import { useEffect, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { api, fechaHora, mes, numero, type Contenido } from '../api'
import { Estado, Placa } from '../componentes'
import { Titulo } from './Layout'

type Indicador = { codigo: string; version: number; nombre: string; tipo_base: string; unidad: string; fase: string; formula: string; observaciones: number; vigente_desde: string }

export function Indicadores() {
  const [lista, setLista] = useState<Indicador[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  useEffect(() => { api<Indicador[]>('/admin/indicadores').then(setLista).catch(e => setError(e.message)) }, [])
  return (
    <>
      <Titulo titulo="Indicadores" descripcion="Versiones registradas desde el diccionario (docs/diccionario_indicadores.yaml). Un cambio de fórmula crea una versión nueva y no altera los datos históricos." />
      <Estado cargando={!lista && !error} error={error}>
        <div className="overflow-x-auto border border-linea bg-papel">
          <table className="tabla min-w-[820px]">
            <thead><tr><th>Código</th><th>Indicador</th><th>Fórmula</th><th>Unidad</th><th>Fase</th><th className="text-right">Valores</th></tr></thead>
            <tbody>
              {lista?.map(i => (
                <tr key={`${i.codigo}-${i.version}`}>
                  <td className="whitespace-nowrap"><Placa codigo={i.codigo} /> <span className="text-xs text-piedra">v{i.version}</span></td>
                  <td>{i.nombre}</td>
                  <td className="numero text-xs">{i.formula}</td>
                  <td className="text-piedra">{i.unidad}</td>
                  <td><span className="pastilla text-piedra">{i.fase?.replace('_', ' ')}</span></td>
                  <td className="numero text-right">{numero(i.observaciones)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Estado>
    </>
  )
}

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

export function ContenidoSitio() {
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
      <Titulo titulo="Contenido del sitio" descripcion="Textos de la página de inicio. Los cambios se publican al guardar.">
        <Link to="/" target="_blank" className="boton-sec">Ver página de inicio</Link>
      </Titulo>
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

type Evento = { id: number; ocurrido_en: string; usuario: string | null; accion: string; entidad: string | null; entidad_id: string | null; resultado: string; detalle: Record<string, unknown> | null }

export function Auditoria() {
  const [lista, setLista] = useState<Evento[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  useEffect(() => { api<Evento[]>('/admin/auditoria').then(setLista).catch(e => setError(e.message)) }, [])
  const clase: Record<string, string> = { ok: 'text-rio', error: 'text-alerta', denegado: 'text-critico' }
  return (
    <>
      <Titulo titulo="Auditoría" descripcion="Últimas 300 acciones críticas: ingresos, cargas, cambios de configuración y exportaciones." />
      <Estado cargando={!lista && !error} error={error}>
        <div className="overflow-x-auto border border-linea bg-papel">
          <table className="tabla min-w-[760px]">
            <thead><tr><th>Fecha</th><th>Usuario</th><th>Acción</th><th>Objeto</th><th>Resultado</th></tr></thead>
            <tbody>
              {lista?.map(e => (
                <tr key={e.id}>
                  <td className="whitespace-nowrap">{fechaHora(e.ocurrido_en)}</td>
                  <td className="break-all">{e.usuario ?? (e.detalle?.correo as string | undefined) ?? '—'}</td>
                  <td>{e.accion.replace('_', ' ')}</td>
                  <td className="text-piedra">{e.entidad ? `${e.entidad} ${e.entidad_id ?? ''}` : '—'}</td>
                  <td><span className={`pastilla ${clase[e.resultado]}`}>{e.resultado}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Estado>
    </>
  )
}

type Reporte = { periodo: string; habitaciones_noche_disponibles: number; habitaciones_noche_ocupadas: number; llegadas: number; noches: number; ingreso_habitaciones_usd: string | null }

export function MisReportes() {
  const [lista, setLista] = useState<Reporte[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  useEffect(() => { api<Reporte[]>('/admin/mis-reportes').then(setLista).catch(e => setError(e.message)) }, [])
  return (
    <>
      <Titulo titulo="Mis reportes" descripcion="Reportes vigentes de su establecimiento. Solo usted y el equipo del observatorio ven estas cifras individuales." />
      <Estado cargando={!lista && !error} error={error}>
        <div className="overflow-x-auto border border-linea bg-papel">
          <table className="tabla min-w-[640px]">
            <thead><tr><th>Mes</th><th className="text-right">Ocupación</th><th className="text-right">Llegadas</th><th className="text-right">Noches</th><th className="text-right">ADR</th></tr></thead>
            <tbody>
              {lista?.map(r => (
                <tr key={r.periodo}>
                  <td>{mes(r.periodo)}</td>
                  <td className="numero text-right">{numero(r.habitaciones_noche_ocupadas / r.habitaciones_noche_disponibles * 100, 1)} %</td>
                  <td className="numero text-right">{numero(r.llegadas)}</td>
                  <td className="numero text-right">{numero(r.noches)}</td>
                  <td className="numero text-right">{r.ingreso_habitaciones_usd ? `$${numero(Number(r.ingreso_habitaciones_usd) / r.habitaciones_noche_ocupadas, 2)}` : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Estado>
    </>
  )
}
