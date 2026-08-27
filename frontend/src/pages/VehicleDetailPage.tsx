import { Link, useParams } from 'react-router-dom'

import { Button } from '@/components/ui/button'

export function VehicleDetailPage() {
  // Só existe pra provar que o parâmetro de rota chega até a página —
  // conteúdo real (buscar o veículo, etc.) é escopo dos Prompts 28-38.
  const { id } = useParams<{ id: string }>()

  return (
    <div className="flex flex-col items-start gap-4">
      <div>Detalhe do veículo #{id} (Prompts 28-38)</div>
      {/* Acesso provisório até a tela de detalhe existir de verdade
          (Prompt 32) — sem isso, /vehicles/:id/edit não tem link nenhum
          apontando pra ela em lugar algum da UI. */}
      <Button asChild variant="outline">
        <Link to={`/vehicles/${id}/edit`}>Editar veículo</Link>
      </Button>
    </div>
  )
}
