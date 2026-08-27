// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { fireEvent } from '@testing-library/dom'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { AuthSessionWatcher } from '@/components/AuthSessionWatcher'
import { RequireAuth } from '@/components/RequireAuth'
import { useLogin } from '@/hooks/useLogin'
import { apiFetch } from '@/services/api'
import { currentUserQueryKey } from '@/services/auth'

function jsonResponse(body: unknown, status: number) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

/** Simula um formulário de login (ou modal de reautenticação) montado ao
 * lado de conteúdo protegido — o cenário concreto em que a falta de
 * distinção entre 401 de login e 401 de sessão quebraria. */
function LoginAttempter() {
  const login = useLogin()
  return (
    <button onClick={() => login.mutate({ username: 'demo', password: 'wrong' })}>
      Tentar login errado
    </button>
  )
}

/** Simula uma segunda chamada protegida (não é login) recebendo 401 — o
 * caso real de sessão expirada no meio do uso, que o evento global PRECISA
 * continuar tratando. */
function ProtectedCallTrigger() {
  return (
    <button onClick={() => void apiFetch('/api/some-protected-endpoint/').catch(() => {})}>
      Disparar chamada protegida
    </button>
  )
}

function renderProtectedTree(client: QueryClient, extra?: React.ReactNode) {
  return render(
    <QueryClientProvider client={client}>
      <AuthSessionWatcher />
      <MemoryRouter initialEntries={['/protected']}>
        <Routes>
          <Route
            path="/protected"
            element={
              <>
                <RequireAuth>
                  <p>Conteúdo protegido</p>
                </RequireAuth>
                {extra}
              </>
            }
          />
          <Route path="/login" element={<p>Marcador da página de login</p>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('RequireAuth', () => {
  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
  })

  it('não reage a um 401 de tentativa de login, mesmo montado em paralelo (isAuthAttempt)', async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const url = String(input)
      if (url.includes('/api/auth/me/')) {
        return Promise.resolve(jsonResponse({ id: 1, username: 'demo' }, 200))
      }
      if (url.includes('/api/auth/login/')) {
        return Promise.resolve(jsonResponse({ detail: 'Usuário e/ou senha incorreto(s)' }, 401))
      }
      throw new Error(`unexpected fetch: ${url}`)
    })
    vi.stubGlobal('fetch', fetchMock)

    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    renderProtectedTree(client, <LoginAttempter />)

    await screen.findByText('Conteúdo protegido')

    fireEvent.click(screen.getByText('Tentar login errado'))

    // espera a mutation de login terminar (com erro) antes de checar que nada mudou
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/api/auth/login/'),
      expect.anything(),
    ))
    await new Promise((r) => setTimeout(r, 50))

    // continua autenticado — não foi pro /login, cache do usuário intacto
    // (getByText já lança se não encontrar, então chegar aqui é a prova)
    screen.getByText('Conteúdo protegido')
    expect(screen.queryByText('Marcador da página de login')).toBeNull()
    expect(client.getQueryData(currentUserQueryKey)).toEqual({ id: 1, username: 'demo' })
  })

  it('controle: um 401 de chamada protegida de verdade (não login) ainda redireciona pro /login', async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const url = String(input)
      if (url.includes('/api/auth/me/')) {
        return Promise.resolve(jsonResponse({ id: 1, username: 'demo' }, 200))
      }
      if (url.includes('/api/some-protected-endpoint/')) {
        return Promise.resolve(jsonResponse({ detail: 'sessão expirada' }, 401))
      }
      throw new Error(`unexpected fetch: ${url}`)
    })
    vi.stubGlobal('fetch', fetchMock)

    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    renderProtectedTree(client, <ProtectedCallTrigger />)

    await screen.findByText('Conteúdo protegido')

    fireEvent.click(screen.getByText('Disparar chamada protegida'))

    await screen.findByText('Marcador da página de login')
    expect(client.getQueryData(currentUserQueryKey)).toBeNull()
  })

  it('erro de rede/servidor em /me/ não redireciona pro /login — mostra estado de erro próprio', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))

    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    renderProtectedTree(client)

    await screen.findByText('Não foi possível verificar sua sessão.')

    expect(screen.queryByText('Marcador da página de login')).toBeNull()
    expect(screen.queryByText('Conteúdo protegido')).toBeNull()
    screen.getByText('Tentar de novo')
  })
})
