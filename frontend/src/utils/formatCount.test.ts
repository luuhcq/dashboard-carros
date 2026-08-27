import { describe, expect, it } from 'vitest'

import { formatCount } from './formatCount'

describe('formatCount', () => {
  it('formata uma contagem pequena', () => {
    expect(formatCount(3)).toBe('3')
  })

  it('formata zero (estoque vazio)', () => {
    expect(formatCount(0)).toBe('0')
  })

  it('formata contagem grande com separador de milhar', () => {
    expect(formatCount(1200)).toBe('1.200')
  })

  it('retorna travessão para null', () => {
    expect(formatCount(null)).toBe('—')
  })

  it('retorna travessão para undefined', () => {
    expect(formatCount(undefined)).toBe('—')
  })
})
