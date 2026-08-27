import { useParams } from 'react-router-dom'

export function VehicleDetailPage() {
  // Só existe pra provar que o parâmetro de rota chega até a página —
  // conteúdo real (buscar o veículo, etc.) é escopo dos Prompts 28-38.
  const { id } = useParams<{ id: string }>()

  return <div>Detalhe do veículo #{id} (Prompts 28-38)</div>
}
