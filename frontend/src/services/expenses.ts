import { apiFetch } from '@/services/api'
import type { VehicleExpense, VehicleExpenseCreatePayload } from '@/types/expense'

export async function fetchVehicleExpenses(vehicleId: string): Promise<VehicleExpense[]> {
  return apiFetch<VehicleExpense[]>(`/api/vehicles/${vehicleId}/expenses/`)
}

export async function createVehicleExpense(
  vehicleId: string,
  payload: VehicleExpenseCreatePayload,
): Promise<VehicleExpense> {
  return apiFetch<VehicleExpense>(`/api/vehicles/${vehicleId}/expenses/`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

/** DELETE aceita corpo (soft delete, exige deletion_reason) — 204 sem corpo
 * de resposta, apiFetch já trata isso retornando undefined. */
export async function deleteVehicleExpense(
  expenseId: string,
  deletionReason: string,
): Promise<void> {
  return apiFetch<void>(`/api/expenses/${expenseId}/`, {
    method: 'DELETE',
    body: JSON.stringify({ deletion_reason: deletionReason }),
  })
}
