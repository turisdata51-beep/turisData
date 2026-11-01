import { unidadCorta, valorKpi } from '../lib/formato'
import type { Kpi } from '../lib/tipos'

/** Código del indicador (A1, B4…) con el estilo de placa. */
export function Placa({ codigo }: { codigo: string }) {
  return <span className="placa" title={`Indicador ${codigo}`}>{codigo}</span>
}

/** Variación frente al mismo mes del año anterior. */
export function Variacion({ valor }: { valor: number | null }) {
  if (valor === null) return <span className="text-sm text-piedra">sin comparación</span>
  const sube = valor >= 0
  return (
    <span className={`text-sm ${sube ? 'text-rio' : 'text-critico'}`}>
      {sube ? '+' : '−'}{Math.abs(valor).toLocaleString('es-EC', { maximumFractionDigits: 1 })} % frente al año anterior
    </span>
  )
}

/** Pieza de la rejilla de indicadores. Va dentro de un contenedor .lechada, que pone las juntas. */
export function TarjetaKpi({ kpi }: { kpi: Kpi }) {
  const unidad = unidadCorta(kpi.unidad)
  return (
    <article className="flex flex-col gap-3 p-5">
      <div className="flex items-start justify-between gap-3">
        <Placa codigo={kpi.codigo} />
        {kpi.bandera === 'estimado' && <span className="pastilla text-alerta" title="Usa la población del último censo disponible">estimado</span>}
      </div>
      <h3 className="font-texto text-[0.95rem] font-semibold leading-snug tracking-normal text-piedra">{kpi.nombre}</h3>
      <div className="mt-auto">
        <p className="cifra text-[2.3rem] text-tinta">{valorKpi(kpi.valor, kpi.unidad)}</p>
        <p className="mt-1 min-h-5 text-sm text-piedra">{unidad}</p>
      </div>
      <Variacion valor={kpi.variacion_interanual} />
    </article>
  )
}
