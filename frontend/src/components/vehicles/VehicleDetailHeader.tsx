import { Link } from 'react-router-dom'

import { Button } from '@/components/ui/button'
import { AddExpenseDialog } from '@/components/vehicles/AddExpenseDialog'
import { VehicleStatusBadge } from '@/components/vehicles/VehicleStatusBadge'
import type { VehicleDetail } from '@/types/vehicle'
import { formatMileage } from '@/utils/formatMileage'

/**
 * Ações do briefing original que ainda não têm tela (Prompt 35/36) —
 * aparecem desabilitadas com "(em breve)" em vez de somem sem explicação
 * ou ficarem clicáveis sem fazer nada: um botão que não responde ao clique
 * é pior que um botão visivelmente desabilitado, porque parece bug em vez
 * de "ainda não existe". "Adicionar despesa" saiu dessa lista no Prompt 33
 * — agora é o AddExpenseDialog de verdade, não mais um placeholder.
 */
const UPCOMING_ACTIONS = ['Alterar preço', 'Registrar venda']

export function VehicleDetailHeader({ vehicle }: { vehicle: VehicleDetail }) {
  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-semibold">
              {vehicle.brand} {vehicle.model}
              {vehicle.version && (
                <span className="ml-2 font-normal text-muted-foreground">{vehicle.version}</span>
              )}
            </h1>
            <VehicleStatusBadge status={vehicle.status} />
          </div>
          {vehicle.internal_code && (
            <p className="mt-1 text-sm text-muted-foreground">{vehicle.internal_code}</p>
          )}
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Button asChild variant="outline">
            <Link to={`/vehicles/${vehicle.id}/edit`}>Editar veículo</Link>
          </Button>
          <AddExpenseDialog vehicleId={vehicle.id} />
          {UPCOMING_ACTIONS.map((label) => (
            <Button key={label} variant="outline" disabled>
              {label} <span className="text-xs text-muted-foreground">(em breve)</span>
            </Button>
          ))}
        </div>
      </div>

      <dl className="flex flex-wrap gap-x-8 gap-y-2 text-sm">
        <div className="flex gap-1.5">
          <dt className="text-muted-foreground">Ano fabricação:</dt>
          <dd className="font-medium">{vehicle.manufacture_year ?? '—'}</dd>
        </div>
        <div className="flex gap-1.5">
          <dt className="text-muted-foreground">Ano modelo:</dt>
          <dd className="font-medium">{vehicle.model_year ?? '—'}</dd>
        </div>
        <div className="flex gap-1.5">
          <dt className="text-muted-foreground">KM:</dt>
          <dd className="font-medium">{formatMileage(vehicle.mileage)}</dd>
        </div>
      </dl>
    </div>
  )
}
