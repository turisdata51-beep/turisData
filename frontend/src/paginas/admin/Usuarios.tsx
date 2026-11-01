import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { Estado } from '../../componentes/Estado'
import { TituloSeccion } from '../../componentes/TituloSeccion'
import { api } from '../../lib/api'
import { fechaHora } from '../../lib/formato'
import { NOMBRE_ROL, type Rol } from '../../lib/tipos'
import { useSesion } from '../../sesion/sesion'

type Usuario = { id: number; correo: string; nombre: string; rol: Rol; activo: boolean; ultimo_acceso: string | null; establecimiento: string | null }
const ROLES: Rol[] = ['administrador', 'analista', 'consulta', 'asociado']
const DESCRIPCION_ROL: Record<Rol, string> = {
  administrador: 'Todo el panel, usuarios y contenido del sitio',
  analista: 'Cargas, establecimientos e indicadores',
  consulta: 'Resumen, indicadores y exportación',
  asociado: 'Solo sube y ve los reportes de su establecimiento',
}

export default function Usuarios() {
  const { usuario: yo } = useSesion()
  const [lista, setLista] = useState<Usuario[] | null>(null)
  const [nuevo, setNuevo] = useState(false)
  const [form, setForm] = useState({ correo: '', nombre: '', rol: 'consulta' as Rol, contrasena: '', codigo_establecimiento: '' })
  const [error, setError] = useState<string | null>(null)
  const [mensaje, setMensaje] = useState<string | null>(null)

  const refrescar = useCallback(() => api<Usuario[]>('/admin/usuarios').then(setLista).catch(e => setError(e.message)), [])
  useEffect(() => { refrescar() }, [refrescar])

  async function crear(e: FormEvent) {
    e.preventDefault(); setError(null)
    try {
      await api('/admin/usuarios', { method: 'POST', body: JSON.stringify({ ...form, codigo_establecimiento: form.codigo_establecimiento || null }) })
      setMensaje(`Usuario ${form.correo} creado`); setNuevo(false)
      setForm({ correo: '', nombre: '', rol: 'consulta', contrasena: '', codigo_establecimiento: '' })
      refrescar()
    } catch (err) { setError((err as Error).message) }
  }

  async function cambiar(u: Usuario, cambios: Partial<Usuario>) {
    setError(null)
    try { await api(`/admin/usuarios/${u.id}`, { method: 'PATCH', body: JSON.stringify(cambios) }); refrescar() }
    catch (err) { setError((err as Error).message) }
  }

  return (
    <>
      <TituloSeccion titulo="Usuarios" descripcion="Cuentas con acceso al panel y lo que cada rol puede hacer.">
        <button type="button" className="boton" onClick={() => { setNuevo(v => !v); setMensaje(null) }}>{nuevo ? 'Cerrar formulario' : 'Crear usuario'}</button>
      </TituloSeccion>
      {mensaje && <p className="text-rio" role="status">{mensaje}</p>}
      {error && <p className="text-critico" role="alert">{error}</p>}

      {nuevo && (
        <form onSubmit={crear} className="grid gap-4 border border-rojo bg-papel p-5 sm:grid-cols-2">
          <label className="grid gap-1 text-sm" htmlFor="u-nombre"><span className="font-semibold">Nombre</span><input id="u-nombre" required className="campo" value={form.nombre} onChange={e => setForm({ ...form, nombre: e.target.value })} /></label>
          <label className="grid gap-1 text-sm" htmlFor="u-correo"><span className="font-semibold">Correo</span><input id="u-correo" type="email" required className="campo" value={form.correo} onChange={e => setForm({ ...form, correo: e.target.value })} /></label>
          <label className="grid gap-1 text-sm" htmlFor="u-rol"><span className="font-semibold">Rol</span>
            <select id="u-rol" className="campo" value={form.rol} onChange={e => setForm({ ...form, rol: e.target.value as Rol })}>
              {ROLES.map(r => <option key={r} value={r}>{NOMBRE_ROL[r]}</option>)}
            </select>
            <span className="text-xs text-piedra">{DESCRIPCION_ROL[form.rol]}</span>
          </label>
          <label className="grid gap-1 text-sm" htmlFor="u-contrasena"><span className="font-semibold">Contraseña inicial</span><input id="u-contrasena" type="password" minLength={10} required className="campo" autoComplete="new-password" value={form.contrasena} onChange={e => setForm({ ...form, contrasena: e.target.value })} /><span className="text-xs text-piedra">Mínimo 10 caracteres</span></label>
          {form.rol === 'asociado' && (
            <label className="grid gap-1 text-sm" htmlFor="u-est"><span className="font-semibold">Código del establecimiento</span><input id="u-est" required className="campo" placeholder="DEMO-001" value={form.codigo_establecimiento} onChange={e => setForm({ ...form, codigo_establecimiento: e.target.value })} /></label>
          )}
          <div className="flex items-end"><button className="boton">Crear usuario</button></div>
        </form>
      )}

      <Estado cargando={!lista && !error} error={null}>
        <div className="overflow-x-auto border border-linea bg-papel">
          <table className="tabla min-w-[760px]">
            <thead><tr><th>Nombre</th><th>Correo</th><th>Rol</th><th>Último acceso</th><th>Estado</th><th></th></tr></thead>
            <tbody>
              {lista?.map(u => (
                <tr key={u.id}>
                  <td>{u.nombre}{u.establecimiento && <span className="ml-1 text-xs text-piedra">({u.establecimiento})</span>}</td>
                  <td className="break-all">{u.correo}</td>
                  <td>
                    <select id={`rol-${u.id}`} aria-label={`Rol de ${u.nombre}`} className="campo !py-1 !text-sm" value={u.rol} disabled={u.id === yo?.id}
                      onChange={e => cambiar(u, { rol: e.target.value as Rol })}>
                      {ROLES.map(r => <option key={r} value={r}>{NOMBRE_ROL[r]}</option>)}
                    </select>
                  </td>
                  <td className="whitespace-nowrap text-piedra">{fechaHora(u.ultimo_acceso)}</td>
                  <td>{u.activo ? <span className="pastilla text-rio">activo</span> : <span className="pastilla text-piedra">inactivo</span>}</td>
                  <td className="text-right">
                    {u.id !== yo?.id && (
                      <button type="button" className="text-sm font-semibold text-rojo" onClick={() => cambiar(u, { activo: !u.activo })}>
                        {u.activo ? 'Desactivar' : 'Activar'}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Estado>
    </>
  )
}
