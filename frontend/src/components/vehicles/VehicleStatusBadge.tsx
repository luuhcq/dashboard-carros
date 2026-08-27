import { Badge } from '@/components/ui/badge'
import type { VehicleStatus } from '@/types/vehicle'
import { VEHICLE_STATUS_LABELS } from '@/types/vehicle'

const STATUS_BADGE_CLASS: Record<VehicleStatus, string> = {
  PURCHASED: 'border-transparent bg-secondary text-secondary-foreground',
  IN_PREPARATION: 'border-transparent bg-secondary text-secondary-foreground',
  READY: 'border-transparent bg-secondary text-secondary-foreground',
  LISTED: 'border-transparent bg-primary/10 text-primary',
  RESERVED: 'border-transparent bg-warning/15 text-warning-foreground',
  SOLD: 'border-transparent bg-success/10 text-success',
}

export function VehicleStatusBadge({ status }: { status: VehicleStatus }) {
  return <Badge className={STATUS_BADGE_CLASS[status]}>{VEHICLE_STATUS_LABELS[status]}</Badge>
}
