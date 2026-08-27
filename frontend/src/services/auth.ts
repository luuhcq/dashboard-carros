import { ApiError, apiFetch } from '@/services/api'

export interface CurrentUser {
  id: number
  username: string
}

export interface LoginCredentials {
  username: string
  password: string
}

/** Chave da query de "usuário atual" — compartilhada entre hooks e o listener de 401. */
export const currentUserQueryKey = ['auth', 'currentUser'] as const

/**
 * `null` significa "sem sessão válida" (401 tratado aqui, não propagado como
 * erro de query) — a UI trata "deslogado" como um estado normal, não uma
 * falha. Qualquer outro erro (rede, 500) continua sendo propagado.
 */
export async function fetchCurrentUser(): Promise<CurrentUser | null> {
  try {
    return await apiFetch<CurrentUser>('/api/auth/me/')
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) return null
    throw error
  }
}

export async function login(credentials: LoginCredentials): Promise<void> {
  await apiFetch<{ detail: string }>('/api/auth/login/', {
    method: 'POST',
    body: JSON.stringify(credentials),
    // Credencial errada é resposta esperada de formulário, tratada pelo
    // useLogin/LoginPage — não deve disparar o evento global de sessão
    // inválida que rotas protegidas escutam.
    isAuthAttempt: true,
  })
}

export async function logout(): Promise<void> {
  await apiFetch<{ detail: string }>('/api/auth/logout/', { method: 'POST' })
}
