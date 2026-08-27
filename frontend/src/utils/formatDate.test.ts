import { describe, expect, it } from 'vitest'

import { formatDate } from './formatDate'

describe('formatDate', () => {
  it('formata purchase_date do cenário do Prompt 12 (Honda Civic)', () => {
    expect(formatDate('2026-01-05')).toBe('05/01/2026')
  })

  it('formata sale_date do mesmo cenário', () => {
    expect(formatDate('2026-02-10')).toBe('10/02/2026')
  })

  it('não perde um dia por causa do fuso local (America/Sao_Paulo, UTC-3)', () => {
    // "2026-01-05" é meia-noite UTC; sem timeZone: 'UTC' no formatter, um
    // ambiente em UTC-3 mostraria 04/01/2026 em vez de 05/01/2026.
    expect(formatDate('2026-01-05')).not.toBe('04/01/2026')
  })

  it('retorna travessão para null', () => {
    expect(formatDate(null)).toBe('—')
  })

  it('retorna travessão para undefined', () => {
    expect(formatDate(undefined)).toBe('—')
  })

  it('retorna travessão para string vazia', () => {
    expect(formatDate('')).toBe('—')
  })

  it('rejeita formato fora do padrão ISO em vez de interpretar errado (MM-DD-YYYY)', () => {
    // new Date('05-01-2026') seria interpretado pelo parser legado do JS
    // como 1º de maio de 2026 — errado e silencioso. A guarda de formato
    // evita isso.
    expect(formatDate('05-01-2026')).toBe('—')
  })

  it('rejeita data ISO com mês/dia fora do intervalo válido', () => {
    expect(formatDate('2026-13-45')).toBe('—')
  })

  it('rejeita datetime completo (fora do contrato date-only da API)', () => {
    expect(formatDate('2026-01-05T10:00:00Z')).toBe('—')
  })
})
