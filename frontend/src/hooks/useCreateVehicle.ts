import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'

import { createVehicle } from '@/services/vehicles'

export function useCreateVehicle() {
  const queryClient = useQueryClient()
  const navigate = useNavigate()

  return useMutation({
    mutationFn: createVehicle,
    onSuccess: async (vehicle) => {
      // Invalida (não sobrescreve manualmente) — próxima visita a /vehicles
      // busca a lista de novo, com o veículo criado já incluído, sem
      // precisar de reload manual. dashboard-summary também muda com um
      // veículo novo (vehicles_in_stock, capital_employed, etc.) — sem essa
      // segunda invalidação, os cards ficariam com valor desatualizado até
      // o staleTime de 60s expirar sozinho caso já estivessem com cache
      // fresco (ex. usuário que já estava em /vehicles antes de ir cadastrar).
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['vehicles'] }),
        queryClient.invalidateQueries({ queryKey: ['dashboard-summary'] }),
      ])
      navigate(`/vehicles/${vehicle.id}`, { replace: true })
    },
  })
}
