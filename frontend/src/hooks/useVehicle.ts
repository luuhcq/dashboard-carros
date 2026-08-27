import { useQuery } from '@tanstack/react-query'

import { ApiError } from '@/services/api'
import { fetchVehicle } from '@/services/vehicles'

export function useVehicle(id: string) {
  return useQuery({
    queryKey: ['vehicle', id],
    queryFn: () => fetchVehicle(id),
    // 404 (id inválido ou veículo soft-deletado) nunca vai ter sucesso numa
    // segunda tentativa — retentar só atrasa a mensagem de "não encontrado"
    // sem chance de mudar o resultado (achado real: ~1s de atraso extra,
    // o backoff padrão da 1ª retry, confirmado rodando contra o backend de
    // verdade). Outros erros (rede/500) continuam com o retry padrão global
    // (1x, lib/queryClient.ts) — esses podem ser transitórios de verdade.
    retry: (failureCount, error) => {
      if (error instanceof ApiError && error.status === 404) return false
      return failureCount < 1
    },
  })
}
