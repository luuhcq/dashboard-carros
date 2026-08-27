// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen } from '@testing-library/react'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { routes } from '@/router'

function jsonResponse(body: unknown, status: number) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

const MOCK_VEHICLE_DETAIL = {
  id: '42',
  internal_code: 'CAR-000042',
  company: 'company-id',
  brand: 'Honda',
  model: 'Civic',
  version: 'EXL 2.0',
  manufacture_year: null,
  model_year: 2022,
  mileage: 32000,
  plate: null,
  chassis: null,
  color: null,
  status: 'LISTED',
  source: null,
  supplier_name: null,
  purchase_date: '2026-01-05',
  purchase_price: '45000.00',
  fipe_reference_value: '52000.00',
  fipe_code: null,
  asking_price: '55000.00',
  sale_date: null,
  sale_price: null,
  notes: null,
  deleted_at: null,
  deletion_reason: null,
  created_at: '2026-01-05T00:00:00Z',
  updated_at: '2026-01-05T00:00:00Z',
  metrics: {
    total_expenses: '0.00',
    total_cost: '45000.00',
    fipe_percentage_paid: '0.8654',
    fipe_discount: '0.1346',
    projected_profit: '10000.00',
    projected_margin: '0.1818',
    projected_roi: '0.2222',
    profit: null,
    margin: null,
    roi: null,
    days_in_stock: 234,
    aging_bucket: '90+',
    profit_per_day: null,
  },
}

/**
 * VehiclesPage e VehicleDetailPage fazem suas próprias chamadas reais —
 * precisa distinguir listagem (array), detalhe de um id (objeto com
 * metrics) e dashboard-summary (objeto agregado) do mesmo jeito que /me/,
 * senão VehiclePurchaseSection quebra tentando ler
 * `vehicle.metrics.fipe_percentage_paid` de um objeto sem `metrics`.
 */
function stubAuthenticatedFetch() {
  vi.stubGlobal(
    'fetch',
    vi.fn((input: RequestInfo | URL) => {
      const url = String(input)
      if (/\/api\/vehicles\/[^/?]+\/$/.test(url)) {
        return Promise.resolve(jsonResponse(MOCK_VEHICLE_DETAIL, 200))
      }
      if (url.includes('/api/vehicles/')) {
        return Promise.resolve(jsonResponse([], 200))
      }
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
      return Promise.resolve(jsonResponse({ id: 1, username: 'demo' }, 200))
    }),
  )
}

function renderRoutesAt(path: string) {
  // createMemoryRouter com o MESMO array `routes` usado em produção — testa
  // a árvore de rotas de verdade (RequireAuth + AppLayout aninhados), não
  // uma reconstrução paralela que poderia divergir dela.
  const memoryRouter = createMemoryRouter(routes, { initialEntries: [path] })
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <RouterProvider router={memoryRouter} />
    </QueryClientProvider>,
  )
}

describe('estrutura de rotas (RequireAuth + AppLayout)', () => {
  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
  })

  it('sem sessão, uma rota protegida (/vehicles) redireciona pro /login', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(jsonResponse({ detail: 'não autenticado' }, 401)),
    )

    renderRoutesAt('/vehicles')

    await screen.findByText('Acesse o dashboard com seu usuário e senha.')
    expect(screen.queryByText('Estoque')).toBeNull()
  })

  it('sem sessão, outra rota protegida (/vehicles/42) também redireciona pro /login', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(jsonResponse({ detail: 'não autenticado' }, 401)),
    )

    renderRoutesAt('/vehicles/42')

    await screen.findByText('Acesse o dashboard com seu usuário e senha.')
  })

  it('com sessão válida, /vehicles renderiza a página filha certa dentro do AppLayout', async () => {
    stubAuthenticatedFetch()

    renderRoutesAt('/vehicles')

    await screen.findByRole('heading', { name: 'Estoque' })
    // prova que é a página CERTA (não Dashboard, não VehicleDetail) e que o
    // AppLayout (layout route pai) compôs junto — header com o nome do
    // usuário logado presente na mesma árvore renderizada.
    expect(screen.queryByText('Dashboard (Prompt 33)')).toBeNull()
    screen.getByText('demo')
  })

  it('com sessão válida, /vehicles/42 renderiza VehicleDetailPage (não /vehicles nem /)', async () => {
    stubAuthenticatedFetch()

    renderRoutesAt('/vehicles/42')

    await screen.findByRole('heading', { name: /Honda Civic/ })
    expect(screen.queryByRole('heading', { name: 'Estoque' })).toBeNull()
  })

  it('rota desconhecida renderiza NotFoundPage', async () => {
    // NotFoundPage não depende de sessão (fica fora do RequireAuth) — não
    // deveria chamar a API; qualquer chamada aqui é sinal de regressão.
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('fetch não deveria ser chamado')))

    renderRoutesAt('/isso-nao-existe')

    await screen.findByText('Página não encontrada')
  })
})
