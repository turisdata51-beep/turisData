import { describe, expect, it } from 'vitest'
import { fecha, mes, numero, trimestre, unidadCorta, valorKpi } from './formato'

describe('mes', () => {
  it('nombra el mes y el año', () => {
    expect(mes('2026-09-01')).toBe('septiembre 2026')
    expect(mes('2025-01-01', true)).toBe('ene 25')
  })
  it('muestra una raya cuando no hay período', () => {
    expect(mes(null)).toBe('—')
    expect(mes('')).toBe('—')
  })
})

describe('trimestre', () => {
  it('nombra los meses del trimestre', () => {
    expect(trimestre('2026-07-01')).toBe('julio a septiembre 2026')
    expect(trimestre('2026-01-01', true)).toBe('T1 26')
    expect(trimestre(null)).toBe('—')
  })
})

describe('numero', () => {
  it('usa punto de miles y coma decimal', () => {
    expect(numero(23732)).toBe('23.732')
    expect(numero(55.7854, 1)).toBe('55,8')
  })
  it('muestra una raya cuando falta el valor', () => {
    expect(numero(null)).toBe('—')
    expect(numero(undefined)).toBe('—')
  })
})

describe('valorKpi', () => {
  it('formatea cada unidad del diccionario', () => {
    expect(valorKpi(55.7854, '%')).toBe('55,8 %')
    expect(valorKpi(73.4916, 'USD por habitación vendida')).toBe('$73,49')
    expect(valorKpi(2.0777, 'noches por llegada')).toBe('2,08')
    expect(valorKpi(37.75, 'noches por 1.000 habitantes')).toBe('37,8')
    expect(valorKpi(11422, 'llegadas')).toBe('11.422')
    expect(valorKpi(250.53, 'litros por noche')).toBe('251')
    expect(valorKpi(11.6467, 'kWh por noche')).toBe('11,6')
    expect(valorKpi(0.9608, 'kg por noche')).toBe('0,96')
  })
  it('el signo % no se separa del número al cortar la línea', () => {
    expect(valorKpi(10, '%')).not.toContain(' %')
  })
  it('muestra una raya cuando el valor es confidencial', () => {
    expect(valorKpi(null, '%')).toBe('—')
  })
})

describe('unidadCorta', () => {
  it('oculta la unidad cuando el valor ya la lleva', () => {
    expect(unidadCorta('%')).toBe('')
    expect(unidadCorta('USD por habitación disponible')).toBe('por habitación disponible')
    expect(unidadCorta('noches')).toBe('noches')
  })
})

describe('fecha', () => {
  it('muestra solo el día, mes y año', () => {
    expect(fecha('2026-11-01T15:39:00Z')).toMatch(/^1 nov\.? 2026$/)
    expect(fecha(null)).toBe('—')
  })
})
