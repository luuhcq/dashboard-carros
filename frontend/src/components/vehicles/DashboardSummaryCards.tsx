import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { useDashboardSummary } from '@/hooks/useDashboardSummary'
import { formatAgingDays } from '@/utils/formatAgingDays'
import { formatCount } from '@/utils/formatCount'
import { formatCurrency } from '@/utils/formatCurrency'

interface SummaryCardProps {
  title: string
  value: string
}

function SummaryCard({ title, value }: SummaryCardProps) {
  return (
    <Card size="sm">
      <CardHeader>
        <CardTitle className="text-sm font-normal text-muted-foreground">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-2xl font-semibold tabular-nums">{value}</p>
      </CardContent>
    </Card>
  )
}

function SummaryCardSkeleton() {
  return (
    <Card size="sm">
      <CardHeader>
        <Skeleton className="h-4 w-24" />
      </CardHeader>
      <CardContent>
        <Skeleton className="h-7 w-20" />
      </CardContent>
    </Card>
  )
}

/**
 * Sempre o estoque inteiro não vendido, nunca reflete os filtros da tabela
 * abaixo — /api/dashboard/summary/ não aceita nenhum query param (decisão
 * documentada, ver Prompt 29): mudar isso seria escopo de backend novo, não
 * cabe aqui.
 */
export function DashboardSummaryCards() {
  const { data: summary, isPending, isError, isRefetching, refetch } = useDashboardSummary()

  if (isPending) {
    return (
      <div className="grid grid-cols-2 gap-4 md:grid-cols-5">
        {Array.from({ length: 5 }).map((_, i) => (
          <SummaryCardSkeleton key={i} />
        ))}
      </div>
    )
  }

  if (isError) {
    // Mesma distinção já usada em RequireAuth/VehiclesTable: erro de
    // rede/servidor não vira "0" ou "—" silencioso — estado próprio, com
    // retry.
    return (
      <Card size="sm">
        <CardContent className="flex flex-col items-center gap-2 py-6 text-center">
          <p className="text-destructive">Não foi possível carregar o resumo do estoque.</p>
          <p className="text-sm text-muted-foreground">
            Verifique sua conexão com o servidor e tente novamente.
          </p>
          <Button variant="outline" size="sm" onClick={() => refetch()} disabled={isRefetching}>
            {isRefetching ? 'Tentando de novo…' : 'Tentar de novo'}
          </Button>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="grid grid-cols-2 gap-4 md:grid-cols-5">
      <SummaryCard title="Veículos em estoque" value={formatCount(summary.vehicles_in_stock)} />
      <SummaryCard title="Capital empregado" value={formatCurrency(summary.capital_employed)} />
      <SummaryCard
        title="Valor pedido agregado"
        value={formatCurrency(summary.total_asking_price)}
      />
      <SummaryCard title="Lucro potencial" value={formatCurrency(summary.potential_profit)} />
      <SummaryCard title="Aging médio" value={formatAgingDays(summary.average_aging_days)} />
    </div>
  )
}
