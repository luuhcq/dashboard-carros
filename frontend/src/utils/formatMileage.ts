const mileageFormatter = new Intl.NumberFormat('pt-BR')

/** Formata quilometragem (inteiro, pode ser null) — "32000" -> "32.000 km". */
export function formatMileage(value: number | null | undefined): string {
  if (value == null) return '—'
  return `${mileageFormatter.format(value)} km`
}
