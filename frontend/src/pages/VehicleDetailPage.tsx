import { Link, useParams } from 'react-router-dom'

import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { VehicleDetailHeader } from '@/components/vehicles/VehicleDetailHeader'
import { VehicleExpensesSection } from '@/components/vehicles/VehicleExpensesSection'
import { VehiclePurchaseSection } from '@/components/vehicles/VehiclePurchaseSection'
import { VehicleResultSection } from '@/components/vehicles/VehicleResultSection'
import { useVehicle } from '@/hooks/useVehicle'
import { ApiError } from '@/services/api'

export function VehicleDetailPage() {
  // A rota (/vehicles/:id) garante que :id sempre existe quando este
  // componente monta (mesmo padrão de VehicleEditPage, Prompt 31).
  const { id = '' } = useParams<{ id: string }>()
  const { data: vehicle, isPending, isError, error, refetch, isRefetching } = useVehicle(id)

  if (isPending) {
    return (
      <div className="flex flex-col gap-6">
        <Skeleton className="h-9 w-96" />
        <Skeleton className="h-40 w-full" />
      </div>
    )
  }

  if (isError) {
    const notFound = error instanceof ApiError && error.status === 404

    // "não encontrado" (id inválido ou veículo soft-deletado) é um estado
    // diferente de erro de rede/servidor — não faz sentido oferecer
    // "tentar de novo" pra um recurso que não existe, e a mensagem certa
    // evita o usuário achar que é um bug transitório.
    if (notFound) {
      return (
        <div className="flex flex-col items-center gap-2 rounded-lg border p-8 text-center">
          <p className="text-destructive">Veículo não encontrado.</p>
          <p className="text-sm text-muted-foreground">
            O veículo pode ter sido removido ou o endereço acessado está incorreto.
          </p>
          <Button asChild variant="outline" size="sm">
            <Link to="/vehicles">Voltar pro estoque</Link>
          </Button>
        </div>
      )
    }

    return (
      <div className="flex flex-col items-center gap-2 rounded-lg border p-8 text-center">
        <p className="text-destructive">Não foi possível carregar este veículo.</p>
        <p className="text-sm text-muted-foreground">
          Verifique sua conexão com o servidor e tente novamente.
        </p>
        <Button variant="outline" size="sm" onClick={() => refetch()} disabled={isRefetching}>
          {isRefetching ? 'Tentando de novo…' : 'Tentar de novo'}
        </Button>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-6">
      <VehicleDetailHeader vehicle={vehicle} />
      <VehiclePurchaseSection vehicle={vehicle} />
      <VehicleExpensesSection vehicle={vehicle} />
      <VehicleResultSection vehicle={vehicle} />
    </div>
  )
}
