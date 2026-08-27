import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import type { useVehicleFilters } from '@/hooks/useVehicleFilters'
import { AGING_BUCKET_LABELS, AGING_BUCKET_OPTIONS, VEHICLE_STATUS_LABELS, VEHICLE_STATUS_OPTIONS } from '@/types/vehicle'
import type { AgingBucket, VehicleStatus } from '@/types/vehicle'

// value="" não é permitido em SelectItem do Radix — "all" é o valor
// sentinela pra "sem filtro", convertido pra null antes de chegar na URL.
const ALL = 'all'

export function VehiclesFilters(filters: ReturnType<typeof useVehicleFilters>) {
  return (
    <div className="flex flex-wrap items-end gap-3">
      <div className="flex flex-col gap-1.5">
        <label htmlFor="vehicle-search" className="text-sm font-medium">
          Buscar
        </label>
        <Input
          id="vehicle-search"
          placeholder="Código, marca, modelo, versão ou placa"
          value={filters.searchInput}
          onChange={(e) => filters.setSearchInput(e.target.value)}
          className="w-64"
        />
      </div>

      <div className="flex flex-col gap-1.5">
        <label htmlFor="vehicle-brand" className="text-sm font-medium">
          Marca
        </label>
        <Input
          id="vehicle-brand"
          value={filters.brandInput}
          onChange={(e) => filters.setBrandInput(e.target.value)}
          className="w-36"
        />
      </div>

      <div className="flex flex-col gap-1.5">
        <label htmlFor="vehicle-model" className="text-sm font-medium">
          Modelo
        </label>
        <Input
          id="vehicle-model"
          value={filters.modelInput}
          onChange={(e) => filters.setModelInput(e.target.value)}
          className="w-36"
        />
      </div>

      <div className="flex flex-col gap-1.5">
        <span className="text-sm font-medium">Status</span>
        <Select
          value={filters.status ?? ALL}
          onValueChange={(value) => filters.setStatus(value === ALL ? null : (value as VehicleStatus))}
        >
          <SelectTrigger className="w-40">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>Todos</SelectItem>
            {VEHICLE_STATUS_OPTIONS.map((option) => (
              <SelectItem key={option} value={option}>
                {VEHICLE_STATUS_LABELS[option]}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="flex flex-col gap-1.5">
        <span className="text-sm font-medium">Aging</span>
        <Select
          value={filters.agingBucket ?? ALL}
          onValueChange={(value) =>
            filters.setAgingBucket(value === ALL ? null : (value as AgingBucket))
          }
        >
          <SelectTrigger className="w-36">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>Todos</SelectItem>
            {AGING_BUCKET_OPTIONS.map((option) => (
              <SelectItem key={option} value={option}>
                {AGING_BUCKET_LABELS[option]}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="flex flex-col gap-1.5">
        <span className="text-sm font-medium">Venda</span>
        <Select
          value={filters.soldFilter}
          onValueChange={(value) => filters.setSoldFilter(value as typeof filters.soldFilter)}
        >
          <SelectTrigger className="w-36">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todos</SelectItem>
            <SelectItem value="sold">Vendidos</SelectItem>
            <SelectItem value="not_sold">Não vendidos</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {filters.hasActiveFilters && (
        <Button variant="ghost" onClick={filters.clearFilters}>
          Limpar filtros
        </Button>
      )}
    </div>
  )
}
