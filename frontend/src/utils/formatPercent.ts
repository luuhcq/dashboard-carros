const percentFormatter = new Intl.NumberFormat('pt-BR', {
  style: 'percent',
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
})

/**
 * Formata uma fração/razão (margin, roi, etc.) vinda do backend como string
 * decimal já em escala 0–1 ("0.1667" -> "16,67%") — o backend documenta
 * explicitamente esse contrato em vehicles/serializers.py: "o frontend
 * multiplica por 100 e formata como percentual". `style: 'percent'` do
 * Intl.NumberFormat já faz essa multiplicação; passar o valor cru (sem
 * multiplicar por 100 de novo) é o comportamento certo aqui.
 */
export function formatPercent(value: string | null | undefined): string {
  if (value == null) return '—'

  const numeric = Number(value)
  if (Number.isNaN(numeric)) return '—'

  return percentFormatter.format(numeric)
}
