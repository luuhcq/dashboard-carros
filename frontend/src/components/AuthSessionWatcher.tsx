import { useAuthUnauthorizedListener } from '@/hooks/useAuthUnauthorizedListener'

/** Não renderiza nada — só mantém o listener de 401 montado perto da raiz. */
export function AuthSessionWatcher() {
  useAuthUnauthorizedListener()
  return null
}
