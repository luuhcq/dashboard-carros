// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from 'vitest'

import { apiFetch, UNAUTHORIZED_EVENT } from './api'

function jsonResponse(body: unknown, status: number) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

describe('apiFetch — evento de 401', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('dispara UNAUTHORIZED_EVENT num 401 comum (sessão expirada/nunca autenticada)', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(jsonResponse({ detail: 'não autenticado' }, 401)),
    )
    const handler = vi.fn()
    window.addEventListener(UNAUTHORIZED_EVENT, handler)

    await expect(apiFetch('/api/some-protected-endpoint/')).rejects.toThrow()

    expect(handler).toHaveBeenCalledTimes(1)
    window.removeEventListener(UNAUTHORIZED_EVENT, handler)
  })

  it('NÃO dispara UNAUTHORIZED_EVENT num 401 de tentativa de login (isAuthAttempt: true)', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(jsonResponse({ detail: 'Usuário e/ou senha incorreto(s)' }, 401)),
    )
    const handler = vi.fn()
    window.addEventListener(UNAUTHORIZED_EVENT, handler)

    await expect(
      apiFetch('/api/auth/login/', {
        method: 'POST',
        body: JSON.stringify({ username: 'x', password: 'wrong' }),
        isAuthAttempt: true,
      }),
    ).rejects.toThrow('Usuário e/ou senha incorreto(s)')

    expect(handler).not.toHaveBeenCalled()
    window.removeEventListener(UNAUTHORIZED_EVENT, handler)
  })
})
