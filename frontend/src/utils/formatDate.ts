const ISO_DATE_PATTERN = /^\d{4}-\d{2}-\d{2}$/

const dateFormatter = new Intl.DateTimeFormat('pt-BR', {
  day: '2-digit',
  month: '2-digit',
  year: 'numeric',
  timeZone: 'UTC',
})

/**
 * Formata uma data ISO 8601 ("2026-01-05", como o DRF DateField entrega
 * purchase_date/sale_date) para dd/mm/yyyy.
 *
 * timeZone: 'UTC' é obrigatório aqui: "2026-01-05" é interpretado como
 * meia-noite UTC pelo `Date` nativo, e formatar isso no fuso local (ex.
 * America/Sao_Paulo, UTC-3) sem fixar o timeZone mostraria "04/01/2026" —
 * um dia a menos.
 *
 * A checagem de formato YYYY-MM-DD roda antes do `new Date()` de propósito:
 * o parser legado do `Date` aceita strings fora do padrão ISO (ex.
 * "05-01-2026" vira 1º de maio, não 5 de janeiro) e devolve uma data válida
 * só que errada, em vez de falhar.
 */
export function formatDate(value: string | null | undefined): string {
  if (value == null) return '—'
  if (!ISO_DATE_PATTERN.test(value)) return '—'

  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'

  return dateFormatter.format(date)
}
