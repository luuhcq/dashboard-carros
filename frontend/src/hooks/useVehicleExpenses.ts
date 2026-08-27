import { useQuery } from '@tanstack/react-query'

import { fetchVehicleExpenses } from '@/services/expenses'

export function useVehicleExpenses(vehicleId: string) {
  return useQuery({
    queryKey: ['vehicle-expenses', vehicleId],
    queryFn: () => fetchVehicleExpenses(vehicleId),
  })
}
