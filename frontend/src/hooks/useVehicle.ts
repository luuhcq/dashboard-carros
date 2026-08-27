import { useQuery } from '@tanstack/react-query'

import { fetchVehicle } from '@/services/vehicles'

export function useVehicle(id: string) {
  return useQuery({
    queryKey: ['vehicle', id],
    queryFn: () => fetchVehicle(id),
  })
}
