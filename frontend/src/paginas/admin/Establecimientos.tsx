import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { Estado } from '../../componentes/Estado'
import { TituloSeccion } from '../../componentes/TituloSeccion'
import { api } from '../../lib/api'
import { mes } from '../../lib/formato'

type Establecimiento = {
  id: number; codigo_camara: string; nombre_comercial: string; tipo_alojamiento: string; categoria: string
  parroquia: string; participa_desde: string; participa_hasta: string | null; ultimo_reporte: string | null
}
type Parroquia = { id: number; nombre: string; tipo: string }

const TIPOS = ['Hotel', 'Hostal', 'Hostería', 'Hacienda turística', 'Lodge', 'Resort', 'Refugio', 'Campamento turístico', 'Casa de huéspedes']
const CATEGORIAS = ['1 estrella', '2 estrellas', '3 estrellas', '4 estrellas', '5 estrellas', 'Categoría única']
const VACIO = { codigo_camara: '', nombre_comercial: '', tipo_alojamiento: 'Hotel', categoria: '3 estrellas', parroquia: 'El Sagrario', participa_desde: new Date().toISOString().slice(0, 10), participa_hasta: '' }

export default function Establecimientos() {
  const [lista, setLista] = useState<Establecimiento[] | null>(null)
  const [parroquias, setParroquias] = useState<Parroquia[]>([])
  const [form, setForm] = useState<typeof VACIO | null>(null)
  const [editando, setEditando] = useState<number | null>(null)
  const [filtro, setFiltro] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [mensaje, setMensaje] = useState<string | null>(null)

  const refrescar = useCallback(() => api<Establecimiento[]>('/admin/establecimientos').then(setLista).catch(e => setError(e.message)), [])
  useEffect(() => { refrescar(); api<Parroquia[]>('/admin/parroquias').then(setParroquias) }, [refrescar])

  function abrir(e?: Establecimiento) {
    setMensaje(null); setError(null)
    setEditando(e?.id ?? null)
    setForm(e ? { ...e, participa_hasta: e.participa_hasta ?? '' } : { ...VACIO })
  }

  async function guardar(ev: FormEvent) {
    ev.preventDefault()
    if (!form) return
    try {
      const cuerpo = JSON.stringify({ ...form, participa_hasta: form.participa_hasta || null })
      if (editando) await api(`/admin/establecimientos/${editando}`, { method: 'PUT', body: cuerpo })
      else await api('/admin/establecimientos', { method: 'POST', body: cuerpo })
      setMensaje(editando ? 'Establecimiento actualizado' : 'Establecimiento registrado')
      setForm(null); refrescar()
    } catch (e) { setError((e as Error).message) }
  }

  const campo = (k: keyof typeof VACIO) => ({
    id: `est-${k}`, value: form?.[k] ?? '', className: 'campo',
    onChange: (e: { target: { value: string } }) => setForm(f => f && { ...f, [k]: e.target.value }),
  })
  const visibles = (lista ?? []).filter(e => `${e.codigo_camara} ${e.nombre_comercial} ${e.parroquia}`.toLowerCase().includes(filtro.toLowerCase()))

  return (
    <>
      <TituloSeccion titulo="Establecimientos" descripcion="Alojamientos asociados que reportan al observatorio. El código lo asigna la Cámara; no se registran RUC ni cédulas.">
        <button type="button" className="boton" onClick={() => abrir()}>Registrar establecimiento</button>
      </TituloSeccion>
      {mensaje && <p className="text-rio" role="status">{mensaje}</p>}
      {error && <p className="text-critico" role="alert">{error}</p>}

      {form && (
        <form onSubmit={guardar} className="grid gap-4 border border-rojo bg-papel p-5 sm:grid-cols-2 lg:grid-cols-3">
          <h2 className="text-xl sm:col-span-2 lg:col-span-3">{editando ? 'Editar establecimiento' : 'Nuevo establecimiento'}</h2>
          <label className="grid gap-1 text-sm" htmlFor="est-codigo_camara"><span className="font-semibold">Código Cámara</span><input required {...campo('codigo_camara')} /></label>
          <label className="grid gap-1 text-sm sm:col-span-1 lg:col-span-2" htmlFor="est-nombre_comercial"><span className="font-semibold">Nombre comercial</span><input required {...campo('nombre_comercial')} /></label>
          <label className="grid gap-1 text-sm" htmlFor="est-tipo_alojamiento"><span className="font-semibold">Tipo</span><select {...campo('tipo_alojamiento')}>{TIPOS.map(t => <option key={t}>{t}</option>)}</select></label>
          <label className="grid gap-1 text-sm" htmlFor="est-categoria"><span className="font-semibold">Categoría</span><select {...campo('categoria')}>{CATEGORIAS.map(t => <option key={t}>{t}</option>)}</select></label>
          <label className="grid gap-1 text-sm" htmlFor="est-parroquia"><span className="font-semibold">Parroquia</span>
            <select {...campo('parroquia')}>
              <optgroup label="Urbanas">{parroquias.filter(p => p.tipo === 'urbana').map(p => <option key={p.id}>{p.nombre}</option>)}</optgroup>
              <optgroup label="Rurales">{parroquias.filter(p => p.tipo === 'rural').map(p => <option key={p.id}>{p.nombre}</option>)}</optgroup>
            </select>
          </label>
          <label className="grid gap-1 text-sm" htmlFor="est-participa_desde"><span className="font-semibold">Participa desde</span><input type="date" required {...campo('participa_desde')} /></label>
          <label className="grid gap-1 text-sm" htmlFor="est-participa_hasta"><span className="font-semibold">Participa hasta <span className="font-normal text-piedra">(vacío si sigue activo)</span></span><input type="date" {...campo('participa_hasta')} /></label>
          <div className="flex items-end gap-2">
            <button className="boton">Guardar</button>
            <button type="button" className="boton-sec" onClick={() => setForm(null)}>Cancelar</button>
          </div>
        </form>
      )}

      <div className="flex flex-wrap items-center justify-between gap-3">
        <input id="filtro-establecimientos" className="campo max-w-xs" placeholder="Buscar por código, nombre o parroquia" value={filtro} onChange={e => setFiltro(e.target.value)} />
        <span className="text-sm text-piedra">{visibles.length} establecimientos</span>
      </div>
      <Estado cargando={!lista && !error} error={null}>
        <div className="overflow-x-auto border border-linea bg-papel">
          <table className="tabla min-w-[760px]">
            <thead><tr><th>Código</th><th>Nombre</th><th>Tipo y categoría</th><th>Parroquia</th><th>Último reporte</th><th>Estado</th><th></th></tr></thead>
            <tbody>
              {visibles.map(e => (
                <tr key={e.id}>
                  <td className="numero">{e.codigo_camara}</td>
                  <td>{e.nombre_comercial}</td>
                  <td className="text-piedra">{e.tipo_alojamiento}, {e.categoria}</td>
                  <td>{e.parroquia}</td>
                  <td className="whitespace-nowrap">{mes(e.ultimo_reporte)}</td>
                  <td>{e.participa_hasta ? <span className="pastilla text-piedra">retirado</span> : <span className="pastilla text-rio">activo</span>}</td>
                  <td className="text-right"><button type="button" className="text-sm font-semibold text-rojo" onClick={() => abrir(e)}>Editar</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Estado>
    </>
  )
}
