// Panel: registro de acciones críticas (RF-10).
import { useEffect, useState } from 'react'
import { Estado } from '../../componentes/Estado'
import { TituloSeccion } from '../../componentes/TituloSeccion'
import { api } from '../../lib/api'
import { fechaHora } from '../../lib/formato'

type Evento = { id: number; ocurrido_en: string; usuario: string | null; accion: string; entidad: string | null; entidad_id: string | null; resultado: string; detalle: Record<string, unknown> | null }

export default function Auditoria() {
  const [lista, setLista] = useState<Evento[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  useEffect(() => { api<Evento[]>('/admin/auditoria').then(setLista).catch(e => setError(e.message)) }, [])
  const clase: Record<string, string> = { ok: 'text-rio', error: 'text-alerta', denegado: 'text-critico' }
  return (
    <>
      <TituloSeccion titulo="Auditoría" descripcion="Últimas 300 acciones críticas: ingresos, cargas, cambios de configuración y exportaciones." />
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
