import { useMutation, useQueryClient } from '@tanstack/react-query'

import { createVehicleExpense } from '@/services/expenses'
import type { VehicleExpenseCreatePayload } from '@/types/expense'

export function useCreateVehicleExpense(vehicleId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (payload: VehicleExpenseCreatePayload) =>
      createVehicleExpense(vehicleId, payload),
    onSuccess: async () => {
      // Uma despesa nova muda total_cost/total_expenses do veículo — o que
      // por sua vez muda a coluna "Custo total" da listagem e
      // capital_employed do dashboard (mesmo padrão de invalidação múltipla
      // dos Prompts 30/31, agora incluindo a lista de despesas em si).
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['vehicle-expenses', vehicleId] }),
        queryClient.invalidateQueries({ queryKey: ['vehicle', vehicleId] }),
        queryClient.invalidateQueries({ queryKey: ['vehicles'] }),
        queryClient.invalidateQueries({ queryKey: ['dashboard-summary'] }),
      ])
    },
  })
}
