// Panel: indicadores registrados desde el diccionario, con sus versiones.
import { useEffect, useState } from 'react'
import { Estado } from '../../componentes/Estado'
import { Placa } from '../../componentes/Indicador'
import { TituloSeccion } from '../../componentes/TituloSeccion'
import { api } from '../../lib/api'
import { numero } from '../../lib/formato'

type Indicador = { codigo: string; version: number; nombre: string; tipo_base: string; unidad: string; fase: string; formula: string; observaciones: number; vigente_desde: string }

export default function Indicadores() {
  const [lista, setLista] = useState<Indicador[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  useEffect(() => { api<Indicador[]>('/admin/indicadores').then(setLista).catch(e => setError(e.message)) }, [])
  return (
    <>
      <TituloSeccion titulo="Indicadores" descripcion="Versiones registradas desde el diccionario de indicadores. Un cambio de fórmula crea una versión nueva y no altera los datos históricos." />
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
