/**
 * Campos de GET /api/dashboard/summary/ (backend/vehicles/dashboard_views.py)
 * — nomes conferidos direto no serializer, não os do briefing original
 * (que dizia "inventory_count"; o campo real é "vehicles_in_stock").
 *
 * Calculado sobre veículos não vendidos (exclude status=SOLD), sem
 * nenhum filtro aceito pela API — endpoint não recebe query params.
 * Estoque vazio: contagens/somas vêm "0"/0, nunca null; average_aging_days
 * vem null (média de conjunto vazio é indefinida, diferente de soma/contagem).
 */
export interface DashboardSummary {
  vehicles_in_stock: number
  capital_employed: string
  total_asking_price: string
  potential_profit: string
  average_aging_days: number | null
}
