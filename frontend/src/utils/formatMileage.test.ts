import { describe, expect, it } from 'vitest'

import { formatMileage } from './formatMileage'

describe('formatMileage', () => {
  it('formata quilometragem com separador de milhar', () => {
    expect(formatMileage(32000)).toBe('32.000 km')
  })

  it('formata zero', () => {
    expect(formatMileage(0)).toBe('0 km')
  })

  it('retorna travessão para null', () => {
    expect(formatMileage(null)).toBe('—')
  })

  it('retorna travessão para undefined', () => {
    expect(formatMileage(undefined)).toBe('—')
  })
})
