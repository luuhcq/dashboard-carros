import { useQuery } from '@tanstack/react-query'

import { fetchDashboardSummary } from '@/services/dashboard'

export function useDashboardSummary() {
  return useQuery({
    // Sem params: o endpoint não aceita filtro nenhum (sempre o estoque
    // inteiro não vendido) — só uma entrada de cache possível.
    // staleTime herda o default global (60s, lib/queryClient.ts), mesmo
    // padrão já usado em useVehicles pra dado que muda pouco.
    queryKey: ['dashboard-summary'],
    queryFn: fetchDashboardSummary,
  })
}
