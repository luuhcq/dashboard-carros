import { Navigate } from 'react-router-dom'

import { Button } from '@/components/ui/button'
import { useCurrentUser } from '@/hooks/useCurrentUser'

export function RequireAuth({ children }: { children: React.ReactNode }) {
  const { data: user, isPending, isError, refetch, isRefetching } = useCurrentUser()

  if (isPending) return null

  // Erro de rede/servidor (não 401 — esse caso já virou `data: null` dentro
  // de fetchCurrentUser) não é a mesma coisa que "não autenticado": não dá
  // pra saber se o usuário tem sessão válida ou não, então não redireciona
  // pro /login — mostra um estado próprio, sem nada do visual de login.
  if (isError) {
    return (
      <main className="flex min-h-svh flex-col items-center justify-center gap-3 p-8 text-center">
        <p className="text-destructive">Não foi possível verificar sua sessão.</p>
        <p className="text-sm text-muted-foreground">
          Verifique sua conexão com o servidor e tente novamente.
        </p>
        <Button variant="outline" onClick={() => refetch()} disabled={isRefetching}>
          {isRefetching ? 'Tentando de novo…' : 'Tentar de novo'}
        </Button>
      </main>
    )
  }

  if (!user) return <Navigate to="/login" replace />

  return children
}
