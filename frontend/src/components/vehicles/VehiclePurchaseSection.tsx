import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { VehicleDetail } from '@/types/vehicle'
import { formatCurrency } from '@/utils/formatCurrency'
import { formatDate } from '@/utils/formatDate'
import { formatPercent } from '@/utils/formatPercent'

function DetailField({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-sm text-muted-foreground">{label}</dt>
      <dd className="font-medium">{value}</dd>
    </div>
  )
}

export function VehiclePurchaseSection({ vehicle }: { vehicle: VehicleDetail }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Compra</CardTitle>
      </CardHeader>
      <CardContent>
        <dl className="grid grid-cols-2 gap-4 md:grid-cols-4">
          <DetailField label="Data da compra" value={formatDate(vehicle.purchase_date)} />
          <DetailField label="Valor de compra" value={formatCurrency(vehicle.purchase_price)} />
          <DetailField label="Origem" value={vehicle.source ?? '—'} />
          <DetailField label="Fornecedor" value={vehicle.supplier_name ?? '—'} />
          <DetailField
            label="FIPE de referência"
            value={formatCurrency(vehicle.fipe_reference_value)}
          />
          <DetailField label="Código FIPE" value={vehicle.fipe_code ?? '—'} />
          {/* Vêm de metrics (calculadas no backend, Prompt 12), não
              recalculadas aqui — null quando fipe_reference_value é null
              (sem referência, não tem o que comparar), formatPercent já
              trata isso como "—". */}
          <DetailField
            label="% FIPE pago"
            value={formatPercent(vehicle.metrics.fipe_percentage_paid)}
          />
          <DetailField label="Desconto sobre FIPE" value={formatPercent(vehicle.metrics.fipe_discount)} />
        </dl>
      </CardContent>
    </Card>
  )
}
