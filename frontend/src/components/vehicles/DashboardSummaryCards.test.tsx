// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { DashboardSummaryCards } from '@/components/vehicles/DashboardSummaryCards'
import { useVehicles } from '@/hooks/useVehicles'

function jsonResponse(body: unknown, status: number) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

const FULL_SUMMARY = {
  vehicles_in_stock: 6,
  capital_employed: '288000.00',
  total_asking_price: '253500.00',
  potential_profit: '25500.00',
  average_aging_days: 138.8,
}

/** Monta os cards ao lado de uma query independente de verdade
 * (useVehicles, a mesma que a tabela do Prompt 28 usa) — igual à
 * composição real de VehiclesPage, pra provar isolamento de verdade, não
 * só simular. */
function VehiclesProbe() {
  const { data, isPending, isError } = useVehicles({})
  if (isPending) return <p>vehicles-probe: carregando</p>
  if (isError) return <p>vehicles-probe: erro</p>
  return <p>vehicles-probe: {data?.length ?? 0} veículos</p>
}

function renderCards(client: QueryClient) {
  return render(
    <QueryClientProvider client={client}>
      <DashboardSummaryCards />
      <VehiclesProbe />
    </QueryClientProvider>,
  )
}

describe('DashboardSummaryCards', () => {
  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
  })

  it('mostra skeleton enquanto a query está pendente, sem os títulos dos cards', () => {
    // never resolve — mantém a query em isPending de propósito
    vi.stubGlobal('fetch', vi.fn(() => new Promise(() => {})))
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })

    const { container } = renderCards(client)

    expect(screen.queryByText('Veículos em estoque')).toBeNull()
    expect(container.querySelectorAll('[data-slot="skeleton"]').length).toBe(10) // 5 cards × 2 skeletons
  })

  it('renderiza os 5 valores corretamente a partir da resposta da API', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn((input: RequestInfo | URL) => {
        const url = String(input)
        if (url.includes('/api/dashboard/summary/')) {
          return Promise.resolve(jsonResponse(FULL_SUMMARY, 200))
        }
        return Promise.resolve(jsonResponse([], 200))
      }),
    )
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })

    renderCards(client)

    await screen.findByText('Veículos em estoque')
    screen.getByText('6')
    screen.getByText('R$ 288.000,00')
    screen.getByText('R$ 253.500,00')
    screen.getByText('R$ 25.500,00')
    // 138.8 arredonda pra 139 (formatAgingDays.ts) — não recalculado aqui,
    // só confere o que o componente mostra pro usuário.
    screen.getByText('139 dias')
  })

  it('average_aging_days null mostra "—", nunca "NaN dias"', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn((input: RequestInfo | URL) => {
        const url = String(input)
        if (url.includes('/api/dashboard/summary/')) {
          return Promise.resolve(
            jsonResponse(
              {
                vehicles_in_stock: 0,
                capital_employed: '0.00',
                total_asking_price: '0.00',
                potential_profit: '0.00',
                average_aging_days: null,
              },
              200,
            ),
          )
        }
        return Promise.resolve(jsonResponse([], 200))
      }),
    )
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })

    renderCards(client)

    await screen.findByText('Veículos em estoque')
    expect(screen.queryByText(/NaN/)).toBeNull()
    expect(screen.queryByText('0 dias')).toBeNull()
    screen.getByText('—')
  })

  it('erro isolado em /api/dashboard/summary/ mostra o estado de erro dos cards sem afetar uma query independente que segue bem-sucedida', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn((input: RequestInfo | URL) => {
        const url = String(input)
        if (url.includes('/api/dashboard/summary/')) {
          return Promise.reject(new TypeError('Failed to fetch'))
        }
        if (url.includes('/api/vehicles/')) {
          return Promise.resolve(jsonResponse([{ id: 1 }, { id: 2 }], 200))
        }
        throw new Error(`unexpected fetch: ${url}`)
      }),
    )
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })

    renderCards(client)

    await screen.findByText('Não foi possível carregar o resumo do estoque.')
    screen.getByText('Tentar de novo')
    // nenhum valor de card (nem antigo, nem "0"/"—" inventado) escapou junto com o erro
    expect(screen.queryByText('Veículos em estoque')).toBeNull()

    // a query independente (useVehicles, a mesma da tabela) não foi afetada
    // pelo erro do summary — resolve normal, com os dados dela.
    await screen.findByText('vehicles-probe: 2 veículos')
  })
})
