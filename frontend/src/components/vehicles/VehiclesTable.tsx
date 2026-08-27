import { ArrowDown, ArrowUp, ArrowUpDown } from 'lucide-react'
import type { ReactNode } from 'react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import type { useVehicleFilters } from '@/hooks/useVehicleFilters'
import { cn } from '@/lib/utils'
import type { VehicleListItem, VehicleOrderingField, VehicleStatus } from '@/types/vehicle'
import { VEHICLE_STATUS_LABELS } from '@/types/vehicle'
import { formatCurrency } from '@/utils/formatCurrency'
import { formatDate } from '@/utils/formatDate'
import { formatMileage } from '@/utils/formatMileage'
import { formatPercent } from '@/utils/formatPercent'

const STATUS_BADGE_CLASS: Record<VehicleStatus, string> = {
  PURCHASED: 'border-transparent bg-secondary text-secondary-foreground',
  IN_PREPARATION: 'border-transparent bg-secondary text-secondary-foreground',
  READY: 'border-transparent bg-secondary text-secondary-foreground',
  LISTED: 'border-transparent bg-primary/10 text-primary',
  RESERVED: 'border-transparent bg-warning/15 text-warning-foreground',
  SOLD: 'border-transparent bg-success/10 text-success',
}

const COLUMN_COUNT = 10

interface SortableHeaderProps {
  label: string
  field: VehicleOrderingField
  filters: ReturnType<typeof useVehicleFilters>
}

function SortableHeader({ label, field, filters }: SortableHeaderProps) {
  const direction = filters.getSortDirection(field)
  const Icon = direction === 'asc' ? ArrowUp : direction === 'desc' ? ArrowDown : ArrowUpDown

  return (
    <TableHead>
      <button
        type="button"
        onClick={() => filters.toggleSort(field)}
        className="flex items-center gap-1 hover:text-foreground"
      >
        {label}
        <Icon className={cn('size-3.5', direction ? 'text-foreground' : 'text-muted-foreground/50')} />
      </button>
    </TableHead>
  )
}

function SkeletonRows() {
  return Array.from({ length: 6 }).map((_, rowIndex) => (
    <TableRow key={rowIndex}>
      {Array.from({ length: COLUMN_COUNT }).map((_, colIndex) => (
        <TableCell key={colIndex}>
          <Skeleton className="h-4 w-full max-w-24" />
        </TableCell>
      ))}
    </TableRow>
  ))
}

interface VehiclesTableProps {
  vehicles: VehicleListItem[] | undefined
  isPending: boolean
  isError: boolean
  isRefetching: boolean
  onRetry: () => void
  filters: ReturnType<typeof useVehicleFilters>
}

export function VehiclesTable({
  vehicles,
  isPending,
  isError,
  isRefetching,
  onRetry,
  filters,
}: VehiclesTableProps) {
  let body: ReactNode

  if (isPending) {
    body = <SkeletonRows />
  } else if (isError) {
    // Mesma distinção do Prompt 26: erro de rede/servidor não é tratado
    // genericamente nem misturado com "sem resultados" — estado próprio,
    // com retry.
    body = (
      <TableRow>
        <TableCell colSpan={COLUMN_COUNT} className="py-10 text-center">
          <div className="flex flex-col items-center gap-2">
            <p className="text-destructive">Não foi possível carregar os veículos.</p>
            <p className="text-sm text-muted-foreground">
              Verifique sua conexão com o servidor e tente novamente.
            </p>
            <Button variant="outline" size="sm" onClick={onRetry} disabled={isRefetching}>
              {isRefetching ? 'Tentando de novo…' : 'Tentar de novo'}
            </Button>
          </div>
        </TableCell>
      </TableRow>
    )
  } else if (!vehicles || vehicles.length === 0) {
    body = (
      <TableRow>
        <TableCell colSpan={COLUMN_COUNT} className="py-10 text-center text-muted-foreground">
          Nenhum veículo encontrado com esses filtros.
        </TableCell>
      </TableRow>
    )
  } else {
    body = vehicles.map((vehicle) => (
      <TableRow key={vehicle.id}>
        <TableCell className="font-medium">
          {vehicle.brand} {vehicle.model}
          {vehicle.version && (
            <span className="ml-1 font-normal text-muted-foreground">{vehicle.version}</span>
          )}
        </TableCell>
        <TableCell>{vehicle.model_year ?? '—'}</TableCell>
        <TableCell>{formatMileage(vehicle.mileage)}</TableCell>
        <TableCell>
          <Badge className={STATUS_BADGE_CLASS[vehicle.status]}>
            {VEHICLE_STATUS_LABELS[vehicle.status]}
          </Badge>
        </TableCell>
        <TableCell>{formatDate(vehicle.purchase_date)}</TableCell>
        <TableCell>{formatCurrency(vehicle.fipe_reference_value)}</TableCell>
        <TableCell>{formatCurrency(vehicle.total_cost)}</TableCell>
        <TableCell>{formatCurrency(vehicle.asking_price)}</TableCell>
        <TableCell
          className={
            vehicle.margin != null && Number(vehicle.margin) < 0
              ? 'font-medium text-destructive'
              : 'font-medium text-success'
          }
        >
          {formatPercent(vehicle.margin)}
        </TableCell>
        <TableCell>
          {vehicle.days_in_stock} dias
          <span className="ml-1 text-xs text-muted-foreground">({vehicle.aging_bucket})</span>
        </TableCell>
      </TableRow>
    ))
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <SortableHeader label="Veículo" field="model" filters={filters} />
          <TableHead>Ano</TableHead>
          <TableHead>KM</TableHead>
          <TableHead>Status</TableHead>
          <SortableHeader label="Compra" field="purchase_date" filters={filters} />
          <TableHead>FIPE</TableHead>
          <SortableHeader label="Custo total" field="total_cost" filters={filters} />
          <SortableHeader label="Preço pedido" field="asking_price" filters={filters} />
          <SortableHeader label="Margem" field="margin" filters={filters} />
          <SortableHeader label="Aging" field="days_in_stock" filters={filters} />
        </TableRow>
      </TableHeader>
      <TableBody>{body}</TableBody>
    </Table>
  )
}
