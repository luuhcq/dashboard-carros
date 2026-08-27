import { useMutation, useQueryClient } from '@tanstack/react-query'

import { deleteVehicleExpense } from '@/services/expenses'

export function useDeleteVehicleExpense(vehicleId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ expenseId, deletionReason }: { expenseId: string; deletionReason: string }) =>
      deleteVehicleExpense(expenseId, deletionReason),
    onSuccess: async () => {
      // Mesmo motivo do useCreateVehicleExpense: excluir despesa também
      // muda total_cost/total_expenses, refletido em 4 lugares diferentes.
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['vehicle-expenses', vehicleId] }),
        queryClient.invalidateQueries({ queryKey: ['vehicle', vehicleId] }),
        queryClient.invalidateQueries({ queryKey: ['vehicles'] }),
        queryClient.invalidateQueries({ queryKey: ['dashboard-summary'] }),
      ])
    },
  })
}
