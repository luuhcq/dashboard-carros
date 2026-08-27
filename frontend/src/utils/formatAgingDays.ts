/**
 * Formata average_aging_days (média, já vem do backend arredondada a 1
 * casa decimal — ver dashboard_views.py) pra um rótulo de dias inteiros:
 * "18 dias". Arredondar uma média já calculada pra exibição não é
 * recalcular o agregado, só decidir a precisão mostrada — igual
 * formatCurrency arredondando pra 2 casas.
 *
 * null significa estoque vazio (ou só com vendidos) — média de conjunto
 * vazio é indefinida, nunca 0.
 */
export function formatAgingDays(value: number | null | undefined): string {
  if (value == null) return '—'

  const rounded = Math.round(value)
  return `${rounded} ${rounded === 1 ? 'dia' : 'dias'}`
}
