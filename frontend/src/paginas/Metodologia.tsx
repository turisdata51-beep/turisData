import { useEffect, useState } from 'react'
import { api } from '../api'
import { EncabezadoPublico, Estado, PiePublico, Placa } from '../componentes'

type Ficha = {
  codigo: string; nombre: string; tipo_base: string; definicion_negocio: string; definicion_estadistica: string
  formula_texto: string; unidad: string; periodicidad: string; limitaciones: string; referencias: string[]; fase: string
}

const TIPOS: Record<string, string> = {
  estandar: 'Estándar oficial',
  kpi_sectorial: 'KPI sectorial',
  calculo_operativo: 'Cálculo del observatorio',
  interno: 'Control interno de calidad',
}

export default function Metodologia() {
  const [fichas, setFichas] = useState<Ficha[]>([])
  const [error, setError] = useState<string | null>(null)
  useEffect(() => { api<Ficha[]>('/public/indicadores').then(setFichas).catch(e => setError(e.message)) }, [])

  return (
    <div className="min-h-screen bg-fondo">
      <EncabezadoPublico />
      <main className="marco py-12">
        <h1 className="text-[clamp(1.9rem,4vw,3rem)]">Cómo se calcula cada indicador</h1>
        <p className="mt-4 max-w-[65ch] text-piedra">
          Cada cifra del observatorio sale de una ficha con definición, fórmula, unidad y fuente. Las fórmulas siguen
          IRTS 2008, Eurostat, ETIS 2016 y las definiciones públicas de CoStar/STR. Los indicadores se calculan sobre la
          suma de los reportes, nunca promediando porcentajes de cada establecimiento.
        </p>
        <Estado cargando={!fichas.length && !error} error={error}>
          <div className="mt-10 divide-y divide-linea border-y border-linea">
            {fichas.map(f => (
              <details key={f.codigo} className="group py-4">
                <summary className="flex cursor-pointer list-none flex-wrap items-center gap-3">
                  <Placa codigo={f.codigo} />
                  <span className="font-display text-lg font-semibold">{f.nombre}</span>
                  <span className="pastilla text-piedra">{TIPOS[f.tipo_base] ?? f.tipo_base}</span>
                  <span className="ml-auto text-sm text-rojo group-open:hidden">Ver ficha</span>
                </summary>
                <dl className="mt-4 grid gap-x-8 gap-y-3 text-sm sm:grid-cols-[12rem_1fr]">
                  <dt className="etiqueta">Qué mide</dt><dd className="max-w-[65ch]">{f.definicion_negocio}</dd>
                  <dt className="etiqueta">Definición técnica</dt><dd className="max-w-[65ch]">{f.definicion_estadistica}</dd>
                  <dt className="etiqueta">Fórmula</dt><dd className="overflow-x-auto font-display">{f.formula_texto}</dd>
                  <dt className="etiqueta">Unidad</dt><dd>{f.unidad}, con periodicidad {f.periodicidad}</dd>
                  <dt className="etiqueta">Limitaciones</dt><dd className="max-w-[65ch] text-piedra">{f.limitaciones}</dd>
                  <dt className="etiqueta">Referencias</dt><dd className="text-piedra">{f.referencias?.join('; ')}</dd>
                </dl>
              </details>
            ))}
          </div>
        </Estado>
      </main>
      <PiePublico />
    </div>
  )
}
