export type VehicleStatus =
  | 'PURCHASED'
  | 'IN_PREPARATION'
  | 'READY'
  | 'LISTED'
  | 'RESERVED'
  | 'SOLD'

export type AgingBucket = '0-15' | '16-30' | '31-45' | '46-60' | '61-90' | '90+'

// Labels em PT-BR exatamente iguais às de VehicleStatus.choices no backend
// (vehicles/models.py) — não são uma tradução própria do frontend.
export const VEHICLE_STATUS_LABELS: Record<VehicleStatus, string> = {
  PURCHASED: 'Comprado',
  IN_PREPARATION: 'Em preparação',
  READY: 'Pronto',
  LISTED: 'Anunciado',
  RESERVED: 'Reservado',
  SOLD: 'Vendido',
}

export const VEHICLE_STATUS_OPTIONS = Object.keys(VEHICLE_STATUS_LABELS) as VehicleStatus[]

export const AGING_BUCKET_LABELS: Record<AgingBucket, string> = {
  '0-15': '0–15 dias',
  '16-30': '16–30 dias',
  '31-45': '31–45 dias',
  '46-60': '46–60 dias',
  '61-90': '61–90 dias',
  '90+': '90+ dias',
}

export const AGING_BUCKET_OPTIONS = Object.keys(AGING_BUCKET_LABELS) as AgingBucket[]

/**
 * Campos de VehicleListSerializer (backend/vehicles/serializers.py) —
 * exatamente o que /api/vehicles/ devolve na listagem, nem mais nem menos.
 * Valores monetários e `margin` (fração, não moeda) chegam como string,
 * nunca number — mesmo contrato de sempre (DRF DecimalField).
 */
export interface VehicleListItem {
  id: string
  internal_code: string | null
  brand: string
  model: string
  version: string | null
  model_year: number | null
  mileage: number | null
  status: VehicleStatus
  purchase_date: string
  fipe_reference_value: string | null
  asking_price: string | null
  total_cost: string
  margin: string | null
  aging_bucket: AgingBucket
  days_in_stock: number
}

/** Campos de VehicleFilter (backend/vehicles/filters.py) + `search` (SearchFilter) + `ordering`. */
export interface VehicleListParams {
  status?: VehicleStatus
  brand?: string
  model?: string
  aging_bucket?: AgingBucket
  is_sold?: boolean
  search?: string
  ordering?: string
}

// Só os campos que o backend de fato aceita em ordering_fields
// (VehicleViewSet.ordering_fields) — nunca inventar coluna "ordenável" que
// a API não suporta.
export const VEHICLE_ORDERING_FIELDS = [
  'model',
  'purchase_date',
  'total_cost',
  'asking_price',
  'margin',
  'days_in_stock',
] as const

export type VehicleOrderingField = (typeof VEHICLE_ORDERING_FIELDS)[number]
