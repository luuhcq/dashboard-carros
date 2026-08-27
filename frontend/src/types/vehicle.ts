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

/**
 * Campos cadastrais que POST/PATCH aceitam de fato (VehicleWriteSerializer)
 * — sem `company` (read_only, o backend injeta a única Company existente,
 * Prompt 30), sem `asking_price`/`sale_price`/`sale_date` (bloqueados ou
 * fora de escopo deste formulário) e sem `status` (oculto de propósito —
 * deixa o default PURCHASED do backend agir na criação; na edição, mesma
 * decisão por consistência — mudar status é fluxo próprio, fora de escopo
 * do Prompt 31, ver VehicleForm.tsx).
 */
export interface VehicleWritableFields {
  brand: string
  model: string
  version?: string
  manufacture_year?: number
  model_year?: number
  mileage?: number
  plate?: string
  chassis?: string
  color?: string
  source?: string
  supplier_name?: string
  purchase_date: string
  purchase_price: number
  fipe_reference_value?: number
  fipe_code?: string
  notes?: string
}

/** Payload de POST /api/vehicles/ — todos os campos obrigatórios de VehicleWritableFields presentes. */
export type VehicleCreatePayload = VehicleWritableFields

/**
 * Payload de PATCH /api/vehicles/{id}/ — parcial de verdade (confirmado nos
 * testes do backend, test_patch_common_field_succeeds manda só 1 campo):
 * VehicleForm em modo edit só inclui os campos que o usuário de fato mudou
 * (RHF dirtyFields), nunca reenvia o formulário inteiro.
 */
export type VehicleUpdatePayload = Partial<VehicleWritableFields>

/**
 * Resposta de POST (201) e PATCH (200) — corpo de VehicleWriteSerializer,
 * não o de VehicleListSerializer nem VehicleDetailSerializer (sem métricas
 * calculadas, ver VehicleDetail abaixo). Só o que as telas usam depois de
 * escrever: `id` pra redirecionar pro detalhe do veículo certo.
 */
export interface VehicleWriteResponse {
  id: string
  internal_code: string
}

/**
 * Corpo de GET /api/vehicles/{id}/ (VehicleDetailSerializer) — confirmado
 * via curl no Prompt 30. Inclui asking_price/sale_date/sale_price (aqui só
 * leitura — nenhum formulário deste app os edita) e `metrics`, o objeto de
 * métricas calculadas que a listagem não expõe.
 */
export interface VehicleDetail {
  id: string
  internal_code: string | null
  company: string
  brand: string
  model: string
  version: string | null
  manufacture_year: number | null
  model_year: number | null
  mileage: number | null
  plate: string | null
  chassis: string | null
  color: string | null
  status: VehicleStatus
  source: string | null
  supplier_name: string | null
  purchase_date: string
  purchase_price: string
  fipe_reference_value: string | null
  fipe_code: string | null
  asking_price: string | null
  sale_date: string | null
  sale_price: string | null
  notes: string | null
  deleted_at: string | null
  deletion_reason: string | null
  created_at: string
  updated_at: string
  metrics: {
    total_expenses: string
    total_cost: string
    fipe_percentage_paid: string | null
    fipe_discount: string | null
    projected_profit: string | null
    projected_margin: string | null
    projected_roi: string | null
    profit: string | null
    margin: string | null
    roi: string | null
    days_in_stock: number
    aging_bucket: AgingBucket
    profit_per_day: string | null
  }
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
