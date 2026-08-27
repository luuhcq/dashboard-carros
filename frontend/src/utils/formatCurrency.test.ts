import { describe, expect, it } from 'vitest'

import { formatCurrency } from './formatCurrency'

// Intl.NumberFormat('pt-BR', { style: 'currency' }) separa "R$" do valor com
// um espaco nao-quebravel (U+00A0), nao um espaco comum. Os literais de
// string abaixo contem esse caractere de proposito, nao um espaco regular.
describe('formatCurrency', () => {
  it('formata um valor redondo vindo do backend', () => {
    expect(formatCurrency('45000.00')).toBe('R$ 45.000,00')
  })

  it('formata um valor com centavos nao-triviais (profit_per_day do Prompt 17)', () => {
    expect(formatCurrency('158.33')).toBe('R$ 158,33')
  })

  it('formata total_cost do cenario do Prompt 12', () => {
    expect(formatCurrency('47300.00')).toBe('R$ 47.300,00')
  })

  it('retorna travessao para null', () => {
    expect(formatCurrency(null)).toBe('—')
  })

  it('retorna travessao para undefined', () => {
    expect(formatCurrency(undefined)).toBe('—')
  })

  it('retorna travessao para string nao-numerica', () => {
    expect(formatCurrency('not-a-number')).toBe('—')
  })

  it('formata valor negativo (prejuizo)', () => {
    expect(formatCurrency('-1200.50')).toBe('-R$ 1.200,50')
  })

  it('formata prejuizo real (profit_per_day negativo, -4500.00)', () => {
    // Intl coloca o sinal de menos antes de "R$", nao antes do numero
    // (o hifen vem antes de R$, nao entre R$ e o valor) -- vale conferir
    // explicitamente porque essa e a saida que o storybook usa pra decidir
    // a cor do texto (destructive para negativo, success para positivo).
    expect(formatCurrency('-4500.00')).toBe('-R$ 4.500,00')
  })
})
