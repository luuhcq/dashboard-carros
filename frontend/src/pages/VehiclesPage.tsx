import { VehiclesFilters } from '@/components/vehicles/VehiclesFilters'
import { VehiclesTable } from '@/components/vehicles/VehiclesTable'
import { useVehicleFilters } from '@/hooks/useVehicleFilters'
import { useVehicles } from '@/hooks/useVehicles'

export function VehiclesPage() {
  const filters = useVehicleFilters()
  const { data: vehicles, isPending, isError, isRefetching, refetch } = useVehicles(filters.params)

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-2xl font-semibold">Estoque</h1>

      <VehiclesFilters {...filters} />

      <VehiclesTable
        vehicles={vehicles}
        isPending={isPending}
        isError={isError}
        isRefetching={isRefetching}
        onRetry={() => refetch()}
        filters={filters}
      />
    </div>
  )
}
