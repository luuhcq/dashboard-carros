const API_URL = import.meta.env.VITE_API_URL

/**
 * Disparado quando uma chamada que pressupõe sessão já estabelecida recebe
 * 401 — cookie nunca existiu ou expirou no meio do uso, não dá pra
 * distinguir aqui e não precisa: os dois casos significam "o cookie não
 * representa mais uma sessão válida". Quem decide o que fazer com isso
 * (limpar o cache do usuário atual, redirecionar pro /login) é a camada de
 * auth, não este cliente HTTP — ver services/auth.ts. Evento de DOM em vez
 * de importar o QueryClient aqui mantém este arquivo sem saber o que é
 * "usuário" ou "sessão".
 *
 * NÃO disparado quando `isAuthAttempt: true` é passado — um 401 de uma
 * tentativa de login é resposta esperada de formulário (credencial errada),
 * sempre tratada localmente por quem chamou. Sem essa distinção, um erro de
 * login disparava o mesmo evento de "sessão inválida" que rotas protegidas
 * escutam pra redirecionar — inofensivo hoje só porque nenhuma tela
 * protegida fica montada ao mesmo tempo que um formulário de login, mas
 * quebraria no dia que existir reautenticação sem navegação (ex. modal de
 * "sessão expirou, digite a senha de novo" sobre uma tela protegida).
 */
export const UNAUTHORIZED_EVENT = 'auth:unauthorized'

export class ApiError extends Error {
  status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

export interface ApiFetchOptions extends RequestInit {
  isAuthAttempt?: boolean
}

async function extractErrorMessage(response: Response): Promise<string> {
  try {
    const body: unknown = await response.clone().json()
    if (body && typeof body === 'object' && 'detail' in body && typeof body.detail === 'string') {
      return body.detail
    }
  } catch {
    // corpo não é JSON (ou está vazio) — cai no fallback abaixo
  }
  return `${response.status} ${response.statusText}`
}

export async function apiFetch<T>(path: string, options?: ApiFetchOptions): Promise<T> {
  const { isAuthAttempt, ...init } = options ?? {}

  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    credentials: 'include',
    headers: {
      Accept: 'application/json',
      ...(init.body ? { 'Content-Type': 'application/json' } : {}),
      ...init.headers,
    },
  })

  if (!response.ok) {
    if (response.status === 401 && !isAuthAttempt) {
      window.dispatchEvent(new Event(UNAUTHORIZED_EVENT))
    }
    throw new ApiError(await extractErrorMessage(response), response.status)
  }

  if (response.status === 204) {
    return undefined as T
  }

  return response.json() as Promise<T>
}
