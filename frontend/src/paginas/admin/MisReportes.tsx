// Panel del hotel asociado: sus propios reportes vigentes.
import { useEffect, useState } from 'react'
import { Estado } from '../../componentes/Estado'
import { TituloSeccion } from '../../componentes/TituloSeccion'
import { api } from '../../lib/api'
import { mes, numero } from '../../lib/formato'

type Reporte = { periodo: string; habitaciones_noche_disponibles: number; habitaciones_noche_ocupadas: number; llegadas: number; noches: number; ingreso_habitaciones_usd: string | null }

export default function MisReportes() {
  const [lista, setLista] = useState<Reporte[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  useEffect(() => { api<Reporte[]>('/admin/mis-reportes').then(setLista).catch(e => setError(e.message)) }, [])
  return (
    <>
      <TituloSeccion titulo="Mis reportes" descripcion="Reportes vigentes de su establecimiento. Solo usted y el equipo del observatorio ven estas cifras individuales." />
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
