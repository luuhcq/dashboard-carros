import { ApiStatus } from '@/components/ApiStatus'
import { Button } from '@/components/ui/button'
import { useCurrentUser } from '@/hooks/useCurrentUser'
import { useLogout } from '@/hooks/useLogout'

export function HomePage() {
  const { data: user } = useCurrentUser()
  const logout = useLogout()

  return (
    <main className="flex min-h-svh flex-col items-center justify-center gap-4 p-8">
      <h1 className="text-2xl font-semibold">Dashboard Revenda</h1>

      {user && (
        <div className="flex items-center gap-3">
          <p className="text-muted-foreground">
            Logado como <span className="font-medium text-foreground">{user.username}</span>
          </p>
          <Button
            variant="outline"
            onClick={() => logout.mutate()}
            disabled={logout.isPending}
          >
            {logout.isPending ? 'Saindo…' : 'Sair'}
          </Button>
        </div>
      )}

      <ApiStatus />
    </main>
  )
}
