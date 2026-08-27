import { describe, expect, it } from 'vitest'

import { formatAgingDays } from './formatAgingDays'

describe('formatAgingDays', () => {
  it('arredonda pra baixo e usa plural (cenário real do endpoint: 6.7 -> 7 dias)', () => {
    expect(formatAgingDays(6.7)).toBe('7 dias')
  })

  it('arredonda pra baixo quando a fração é menor que 0.5', () => {
    expect(formatAgingDays(18.2)).toBe('18 dias')
  })

  it('usa singular quando arredonda pra exatamente 1', () => {
    expect(formatAgingDays(1.2)).toBe('1 dia')
  })

  it('formata zero (todo o estoque comprado hoje)', () => {
    expect(formatAgingDays(0)).toBe('0 dias')
  })

  it('retorna travessão para null (estoque vazio ou só com vendidos)', () => {
    expect(formatAgingDays(null)).toBe('—')
  })

  it('retorna travessão para undefined', () => {
    expect(formatAgingDays(undefined)).toBe('—')
  })
})
