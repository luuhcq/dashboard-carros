import { VehicleForm } from '@/components/vehicles/VehicleForm'
import { useCreateVehicle } from '@/hooks/useCreateVehicle'
import type { VehicleCreatePayload } from '@/types/vehicle'

export function VehicleNewPage() {
  const createVehicle = useCreateVehicle()

  return (
    <div className="mx-auto max-w-3xl">
      <h1 className="mb-4 text-2xl font-semibold">Cadastrar veículo</h1>

      <VehicleForm
        mode="create"
        isSubmitting={createVehicle.isPending}
        submitLabel="Cadastrar veículo"
        onSubmit={(payload) => createVehicle.mutateAsync(payload as VehicleCreatePayload)}
      />
    </div>
  )
}
