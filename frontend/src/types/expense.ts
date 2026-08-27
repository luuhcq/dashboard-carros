export type ExpenseCategory =
  | 'ACQUISITION'
  | 'YARD_RELEASE'
  | 'TRANSPORT'
  | 'DOCUMENTATION'
  | 'MECHANICAL'
  | 'BODYWORK'
  | 'PAINTING'
  | 'DETAILING'
  | 'CLEANING'
  | 'PARTS'
  | 'ACCESSORIES'
  | 'MARKETING'
  | 'COMMISSION'
  | 'OTHER'

// Labels em PT-BR exatamente iguais às de ExpenseCategory.choices no backend
// (vehicles/models.py) — mesma convenção de VEHICLE_STATUS_LABELS.
export const EXPENSE_CATEGORY_LABELS: Record<ExpenseCategory, string> = {
  ACQUISITION: 'Aquisição',
  YARD_RELEASE: 'Pátio/Liberação',
  TRANSPORT: 'Transporte',
  DOCUMENTATION: 'Documentação',
  MECHANICAL: 'Mecânica',
  BODYWORK: 'Funilaria',
  PAINTING: 'Pintura',
  DETAILING: 'Estética',
  CLEANING: 'Higienização',
  PARTS: 'Peças',
  ACCESSORIES: 'Acessórios',
  MARKETING: 'Marketing',
  COMMISSION: 'Comissão',
  OTHER: 'Outros',
}

export const EXPENSE_CATEGORY_OPTIONS = Object.keys(EXPENSE_CATEGORY_LABELS) as ExpenseCategory[]

/** Corpo de GET /api/vehicles/{id}/expenses/ (VehicleExpense) — campo
 * booleano se chama `paid`, não `is_paid` (confirmado no model). */
export interface VehicleExpense {
  id: string
  vehicle: string
  date: string
  category: ExpenseCategory
  description: string
  supplier: string | null
  amount: string
  paid: boolean
  notes: string | null
  deleted_at: string | null
  deletion_reason: string | null
  created_at: string
  updated_at: string
}

/**
 * Payload de POST /api/vehicles/{id}/expenses/ — sem `vehicle` (read_only,
 * injetado da URL, igual à decisão de `company` no Prompt 30) e sem
 * `notes` (não faz parte dos campos deste formulário, ver Prompt 33).
 */
export interface VehicleExpenseCreatePayload {
  date: string
  category: ExpenseCategory
  description: string
  supplier?: string
  amount: number
  paid: boolean
}
