import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'

import { currentUserQueryKey, fetchCurrentUser, login } from '@/services/auth'

export function useLogin() {
  const queryClient = useQueryClient()
  const navigate = useNavigate()

  return useMutation({
    mutationFn: login,
    onSuccess: async () => {
      // O login não devolve o usuário no corpo (o backend nunca manda o
      // token, só seta o cookie) — busca /me/ de propósito em vez de só
      // invalidar, pra já ter o usuário em cache quando a rota protegida
      // renderizar, sem um segundo round-trip visível.
      const user = await fetchCurrentUser()
      queryClient.setQueryData(currentUserQueryKey, user)
      navigate('/', { replace: true })
    },
  })
}
