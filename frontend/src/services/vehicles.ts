import { apiFetch } from '@/services/api'
import type { VehicleListItem, VehicleListParams } from '@/types/vehicle'

function buildQueryString(params: VehicleListParams): string {
  const search = new URLSearchParams()

  if (params.status) search.set('status', params.status)
  if (params.brand) search.set('brand', params.brand)
  if (params.model) search.set('model', params.model)
  if (params.aging_bucket) search.set('aging_bucket', params.aging_bucket)
  if (params.is_sold != null) search.set('is_sold', String(params.is_sold))
  if (params.search) search.set('search', params.search)
  if (params.ordering) search.set('ordering', params.ordering)

  const qs = search.toString()
  return qs ? `?${qs}` : ''
}

export async function fetchVehicles(params: VehicleListParams): Promise<VehicleListItem[]> {
  // Endpoint não é paginado (decisão documentada em config/settings/base.py
  // — estoque de uma revenda fica na casa de dezenas/centenas de linhas) —
  // resposta é um array puro, não um envelope {results, count, ...}.
  return apiFetch<VehicleListItem[]>(`/api/vehicles/${buildQueryString(params)}`)
}
