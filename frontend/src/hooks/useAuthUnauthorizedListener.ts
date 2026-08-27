import { useQueryClient } from '@tanstack/react-query'
import { useEffect } from 'react'

import { UNAUTHORIZED_EVENT } from '@/services/api'
import { currentUserQueryKey } from '@/services/auth'

/**
 * Interceptor de 401: qualquer chamada da API (não só /me/) que volte 401
 * marca o usuário atual como deslogado no cache. Quem reage a isso e
 * redireciona é o RequireAuth, que já está inscrito nessa mesma query —
 * este hook só existe pra desacoplar o cliente HTTP (services/api.ts) do
 * conceito de "sessão"/TanStack Query. Monta uma vez, perto da raiz.
 */
export function useAuthUnauthorizedListener() {
  const queryClient = useQueryClient()

  useEffect(() => {
    const handleUnauthorized = () => {
      queryClient.setQueryData(currentUserQueryKey, null)
    }
    window.addEventListener(UNAUTHORIZED_EVENT, handleUnauthorized)
    return () => window.removeEventListener(UNAUTHORIZED_EVENT, handleUnauthorized)
  }, [queryClient])
}
