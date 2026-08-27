const countFormatter = new Intl.NumberFormat('pt-BR')

/** Formata uma contagem simples (ex. vehicles_in_stock) com separador de milhar. */
export function formatCount(value: number | null | undefined): string {
  if (value == null) return '—'
  return countFormatter.format(value)
}
