const currencyFormatter = new Intl.NumberFormat('pt-BR', {
  style: 'currency',
  currency: 'BRL',
})

/**
 * Formata um valor decimal em BRL (pt-BR).
 *
 * A API entrega DecimalField do DRF como string ("47300.00"), não como
 * número — passar essa string direto pro Number()/parseFloat evita o
 * arredondamento de ponto flutuante que um `number` já traria embutido.
 */
export function formatCurrency(value: string | null | undefined): string {
  if (value == null) return '—'

  const numeric = Number(value)
  if (Number.isNaN(numeric)) return '—'

  return currencyFormatter.format(numeric)
}
