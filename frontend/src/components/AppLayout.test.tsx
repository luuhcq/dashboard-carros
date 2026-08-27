// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen } from '@testing-library/react'
import { fireEvent } from '@testing-library/dom'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { AppLayout } from '@/components/AppLayout'

function jsonResponse(body: unknown, status: number) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

function renderAt(path: string) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <AppLayout />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('AppLayout', () => {
  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
  })

  it('destaca "Dashboard" como item ativo quando a rota atual é "/"', () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(jsonResponse({ id: 1, username: 'demo' }, 200)),
    )

    renderAt('/')

    // NavLink marca o link ativo com aria-current="page" por padrão — sinal
    // semântico do próprio React Router, não uma classe CSS que só eu leio.
    expect(screen.getByText('Dashboard').getAttribute('aria-current')).toBe('page')
    expect(screen.getByText('Estoque').getAttribute('aria-current')).toBeNull()
  })

  it('destaca "Estoque" como item ativo quando a rota atual é "/vehicles"', () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(jsonResponse({ id: 1, username: 'demo' }, 200)),
    )

    renderAt('/vehicles')

    expect(screen.getByText('Estoque').getAttribute('aria-current')).toBe('page')
    expect(screen.getByText('Dashboard').getAttribute('aria-current')).toBeNull()
  })

  it('destaca "Estoque" também numa sub-rota (/vehicles/42) — "Dashboard" usa "end" e não casa por prefixo', () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(jsonResponse({ id: 1, username: 'demo' }, 200)),
    )

    renderAt('/vehicles/42')

    expect(screen.getByText('Estoque').getAttribute('aria-current')).toBe('page')
    expect(screen.getByText('Dashboard').getAttribute('aria-current')).toBeNull()
  })

  it('botão "Sair" dispara o logout (useLogout) — chama o endpoint de logout', async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const url = String(input)
      if (url.includes('/api/auth/me/')) {
        return Promise.resolve(jsonResponse({ id: 1, username: 'demo' }, 200))
      }
      if (url.includes('/api/auth/logout/')) {
        return Promise.resolve(jsonResponse({ detail: 'logout realizado com sucesso' }, 200))
      }
      throw new Error(`unexpected fetch: ${url}`)
    })
    vi.stubGlobal('fetch', fetchMock)

    renderAt('/')
    await screen.findByText('demo')

    fireEvent.click(screen.getByText('Sair'))

    await vi.waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining('/api/auth/logout/'),
        expect.objectContaining({ method: 'POST' }),
      )
    })
  })
})
