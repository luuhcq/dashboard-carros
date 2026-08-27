import { describe, expect, it } from 'vitest'

import { formatPercent } from './formatPercent'

describe('formatPercent', () => {
  it('formata a margem do cenário real (10000/60000 quantizado a 4 casas)', () => {
    expect(formatPercent('0.1667')).toBe('16,67%')
  })

  it('formata margem realizada do cenário do Prompt 12 (5700/47300 → como fração)', () => {
    expect(formatPercent('0.1205')).toBe('12,05%')
  })

  it('formata margem negativa (prejuízo)', () => {
    expect(formatPercent('-0.05')).toBe('-5,00%')
  })

  it('formata zero', () => {
    expect(formatPercent('0.0000')).toBe('0,00%')
  })

  it('retorna travessão para null (sem asking_price, sem margin calculável)', () => {
    expect(formatPercent(null)).toBe('—')
  })

  it('retorna travessão para undefined', () => {
    expect(formatPercent(undefined)).toBe('—')
  })

  it('retorna travessão para string não-numérica', () => {
    expect(formatPercent('not-a-number')).toBe('—')
  })
})
