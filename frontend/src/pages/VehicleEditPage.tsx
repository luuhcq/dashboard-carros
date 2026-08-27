import { useParams } from 'react-router-dom'

import { VehicleForm } from '@/components/vehicles/VehicleForm'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { useUpdateVehicle } from '@/hooks/useUpdateVehicle'
import { useVehicle } from '@/hooks/useVehicle'
import type { VehicleDetail, VehicleUpdatePayload } from '@/types/vehicle'

function vehicleDetailToFormDefaults(vehicle: VehicleDetail) {
  return {
    brand: vehicle.brand,
    model: vehicle.model,
    version: vehicle.version ?? '',
    manufacture_year: vehicle.manufacture_year != null ? String(vehicle.manufacture_year) : '',
    model_year: vehicle.model_year != null ? String(vehicle.model_year) : '',
    mileage: vehicle.mileage != null ? String(vehicle.mileage) : '',
    plate: vehicle.plate ?? '',
    chassis: vehicle.chassis ?? '',
    color: vehicle.color ?? '',
    source: vehicle.source ?? '',
    supplier_name: vehicle.supplier_name ?? '',
    purchase_date: vehicle.purchase_date,
    purchase_price: vehicle.purchase_price,
    fipe_reference_value: vehicle.fipe_reference_value ?? '',
    fipe_code: vehicle.fipe_code ?? '',
    notes: vehicle.notes ?? '',
  }
}

export function VehicleEditPage() {
  // A rota (/vehicles/:id/edit) garante que :id sempre existe quando este
  // componente monta — sem isso, useVehicle('') faria uma chamada inválida
  // (mesmo padrão de VehicleDetailPage, Prompt 27).
  const { id = '' } = useParams<{ id: string }>()

  const { data: vehicle, isPending, isError, refetch, isRefetching } = useVehicle(id)
  const updateVehicle = useUpdateVehicle(id)

  return (
    <div className="mx-auto max-w-3xl">
      <h1 className="mb-4 text-2xl font-semibold">Editar veículo</h1>

      {isPending && (
        <div className="flex flex-col gap-3">
          <Skeleton className="h-9 w-full" />
          <Skeleton className="h-9 w-full" />
          <Skeleton className="h-9 w-full" />
        </div>
      )}

      {isError && (
        <div className="flex flex-col items-center gap-2 rounded-lg border p-8 text-center">
          <p className="text-destructive">Não foi possível carregar este veículo.</p>
          <p className="text-sm text-muted-foreground">
            Verifique sua conexão com o servidor e tente novamente.
          </p>
          <Button variant="outline" size="sm" onClick={() => refetch()} disabled={isRefetching}>
            {isRefetching ? 'Tentando de novo…' : 'Tentar de novo'}
          </Button>
        </div>
      )}

      {vehicle && (
        <VehicleForm
          mode="edit"
          defaultValues={vehicleDetailToFormDefaults(vehicle)}
          pricingInfo={{ askingPrice: vehicle.asking_price, salePrice: vehicle.sale_price }}
          isSubmitting={updateVehicle.isPending}
          submitLabel="Salvar alterações"
          onSubmit={(payload) => updateVehicle.mutateAsync(payload as VehicleUpdatePayload)}
        />
      )}
    </div>
  )
}
