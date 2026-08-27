import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { toast } from 'sonner'

import { updateVehicle } from '@/services/vehicles'
import type { VehicleUpdatePayload } from '@/types/vehicle'

export function useUpdateVehicle(id: string) {
  const queryClient = useQueryClient()
  const navigate = useNavigate()

  return useMutation({
    mutationFn: (payload: VehicleUpdatePayload) => updateVehicle(id, payload),
    onSuccess: async () => {
      // Mesmo padrão do Prompt 30 (['vehicles'] + ['dashboard-summary']),
      // mais ['vehicle', id]: o detalhe deste veículo específico também
      // ficaria com dado desatualizado em cache sem essa terceira
      // invalidação — ainda não existe tela nenhuma consumindo essa query
      // key de verdade (VehicleDetailPage é placeholder até o Prompt 32),
      // mas a query key já existe (useVehicle) e o cache dela precisa ser
      // invalidado igual, pra não nascer errado quando a tela existir.
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['vehicles'] }),
        queryClient.invalidateQueries({ queryKey: ['dashboard-summary'] }),
        queryClient.invalidateQueries({ queryKey: ['vehicle', id] }),
      ])
      toast.success('Veículo atualizado.')
      navigate(`/vehicles/${id}`, { replace: true })
    },
  })
}
