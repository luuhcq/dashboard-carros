import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { VehicleStatusBadge } from '@/components/vehicles/VehicleStatusBadge'
import type { VehicleDetail } from '@/types/vehicle'
import { AGING_BUCKET_LABELS } from '@/types/vehicle'
import { formatCurrency } from '@/utils/formatCurrency'
import { formatDate } from '@/utils/formatDate'
import { formatPercent } from '@/utils/formatPercent'

function DetailField({
  label,
  value,
  valueClassName,
}: {
  label: string
  value: string
  valueClassName?: string
}) {
  return (
    <div>
      <dt className="text-sm text-muted-foreground">{label}</dt>
      <dd className={valueClassName ? `font-medium ${valueClassName}` : 'font-medium'}>{value}</dd>
    </div>
  )
}

// null (métrica ainda não calculável, ex. sem asking_price) fica com a cor
// padrão de texto — mesmo tratamento "—" do resto da página, sem verde nem
// vermelho. Só valores numéricos de fato ganham cor semântica.
function profitColorClass(value: string | null): string | undefined {
  if (value == null) return undefined
  const numeric = Number(value)
  if (Number.isNaN(numeric)) return undefined
  return numeric < 0 ? 'text-destructive' : 'text-success'
}

export function VehicleResultSection({ vehicle }: { vehicle: VehicleDetail }) {
  const { metrics } = vehicle
  const isSold = vehicle.status === 'SOLD'

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          Resultado
          {/* Reforça visualmente que este bloco é o realizado (venda já
              aconteceu), não o projetado — os dois nunca aparecem juntos. */}
          {isSold && <VehicleStatusBadge status={vehicle.status} />}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {isSold ? (
          <dl className="grid grid-cols-2 gap-4 md:grid-cols-3">
            <DetailField label="Preço de venda" value={formatCurrency(vehicle.sale_price)} />
            <DetailField label="Data da venda" value={formatDate(vehicle.sale_date)} />
            <DetailField
              label="Lucro realizado"
              value={formatCurrency(metrics.profit)}
              valueClassName={profitColorClass(metrics.profit)}
            />
            <DetailField
              label="Margem"
              value={formatPercent(metrics.margin)}
              valueClassName={profitColorClass(metrics.margin)}
            />
            <DetailField
              label="ROI"
              value={formatPercent(metrics.roi)}
              valueClassName={profitColorClass(metrics.roi)}
            />
            <DetailField
              label="Lucro por dia"
              value={formatCurrency(metrics.profit_per_day)}
              valueClassName={profitColorClass(metrics.profit_per_day)}
            />
            <div>
              <dt className="text-sm text-muted-foreground">Dias em estoque</dt>
              <dd className="flex items-center gap-2 font-medium">
                {metrics.days_in_stock} dias
                <Badge variant="outline">{AGING_BUCKET_LABELS[metrics.aging_bucket]}</Badge>
              </dd>
            </div>
          </dl>
        ) : (
          <dl className="grid grid-cols-2 gap-4 md:grid-cols-4">
            <DetailField label="Preço pedido" value={formatCurrency(vehicle.asking_price)} />
            <DetailField
              label="Lucro projetado"
              value={formatCurrency(metrics.projected_profit)}
              valueClassName={profitColorClass(metrics.projected_profit)}
            />
            <DetailField
              label="Margem projetada"
              value={formatPercent(metrics.projected_margin)}
              valueClassName={profitColorClass(metrics.projected_margin)}
            />
            <DetailField
              label="ROI projetado"
              value={formatPercent(metrics.projected_roi)}
              valueClassName={profitColorClass(metrics.projected_roi)}
            />
          </dl>
        )}
      </CardContent>
    </Card>
  )
}
