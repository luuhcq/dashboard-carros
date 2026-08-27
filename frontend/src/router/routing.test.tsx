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

/** VehiclesPage faz sua própria chamada real a /api/vehicles/ — precisa de
 * uma resposta moldada como array, não o mesmo objeto de /me/. */
function stubAuthenticatedFetch() {
  vi.stubGlobal(
    'fetch',
    vi.fn((input: RequestInfo | URL) => {
      const url = String(input)
      if (url.includes('/api/vehicles/')) {
        return Promise.resolve(jsonResponse([], 200))
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

    await screen.findByText('Detalhe do veículo #42 (Prompts 28-38)')
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
