import { useQuery } from '@tanstack/react-query'

import { currentUserQueryKey, fetchCurrentUser } from '@/services/auth'

export function useCurrentUser() {
  return useQuery({
    queryKey: currentUserQueryKey,
    queryFn: fetchCurrentUser,
    // Sessão não expira sozinha por tempo no cliente — só muda via login,
    // logout ou um 401 vindo de qualquer chamada (ver useAuthUnauthorized).
    // Sem retry: um 401 legítimo (sem sessão) não deve ficar tentando de novo.
    staleTime: Infinity,
    retry: false,
  })
}
