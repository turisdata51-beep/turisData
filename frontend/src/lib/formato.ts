// Formato de fechas, números y valores de indicadores en español de Ecuador.

const MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
const MESES_CORTOS = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']

/** "2026-09-01" → "septiembre 2026" (o "sep 26" si corto). */
export function mes(periodo: string | null | undefined, corto = false): string {
  if (!periodo) return '—'
  const [a, m] = periodo.split('-').map(Number)
  return corto ? `${MESES_CORTOS[m - 1]} ${String(a).slice(2)}` : `${MESES[m - 1]} ${a}`
}

/** "2026-07-01" → "julio a septiembre 2026" (o "T3 26" si corto). */
export function trimestre(periodo: string | null | undefined, corto = false): string {
  if (!periodo) return '—'
  const [a, m] = periodo.split('-').map(Number)
  const t = Math.floor((m - 1) / 3)
  return corto ? `T${t + 1} ${String(a).slice(2)}` : `${MESES[t * 3]} a ${MESES[t * 3 + 2]} ${a}`
}

export function fechaHora(valor: string | null | undefined): string {
  if (!valor) return '—'
  return new Date(valor).toLocaleString('es-EC', { dateStyle: 'medium', timeStyle: 'short' })
}

export function fecha(valor: string | null | undefined): string {
  if (!valor) return '—'
  return new Date(valor).toLocaleDateString('es-EC', { day: 'numeric', month: 'short', year: 'numeric' })
}

export function numero(valor: number | null | undefined, decimales = 0): string {
  if (valor === null || valor === undefined) return '—'
  return valor.toLocaleString('es-EC', { minimumFractionDigits: decimales, maximumFractionDigits: decimales })
}

/** Formatea según la unidad del diccionario de indicadores. El espacio antes de % no se separa. */
export function valorKpi(valor: number | null, unidad: string): string {
  if (valor === null) return '—'
  if (unidad === '%') return `${numero(valor, 1)} %`
  if (unidad.startsWith('USD')) return `$${numero(valor, 2)}`
  if (unidad.startsWith('noches por llegada')) return numero(valor, 2)
  if (unidad.startsWith('noches por 1.000')) return numero(valor, 1)
  if (unidad.startsWith('kWh por noche')) return numero(valor, 1)
  if (unidad.startsWith('kg por noche')) return numero(valor, 2)
  return numero(valor)
}

/** Unidad para mostrar bajo la cifra (vacía cuando el valor ya lleva su símbolo). */
export function unidadCorta(unidad: string): string {
  if (unidad === '%') return ''
  if (unidad.startsWith('USD por habitación vendida')) return 'por habitación vendida'
  if (unidad.startsWith('USD por habitación disponible')) return 'por habitación disponible'
  return unidad
}
