import { useQuery } from '@tanstack/react-query'

import { fetchVehicles } from '@/services/vehicles'
import type { VehicleListParams } from '@/types/vehicle'

export function useVehicles(params: VehicleListParams) {
  return useQuery({
    // Cada combinação de filtro/busca/ordenação é uma entrada de cache
    // distinta — voltar um filtro já usado não refaz a chamada (staleTime
    // padrão de 60s do QueryClient, ver lib/queryClient.ts).
    queryKey: ['vehicles', params],
    queryFn: () => fetchVehicles(params),
  })
}
