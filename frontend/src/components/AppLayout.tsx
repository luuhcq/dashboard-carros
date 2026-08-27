import { NavLink, Outlet } from 'react-router-dom'

import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { useCurrentUser } from '@/hooks/useCurrentUser'
import { useLogout } from '@/hooks/useLogout'

const navItems = [
  { to: '/', label: 'Dashboard', end: true },
  { to: '/vehicles', label: 'Estoque' },
]

export function AppLayout() {
  // Já resolvido pelo RequireAuth (layout route pai) antes deste montar —
  // aqui é só leitura do cache, sem novo estado de loading/erro pra tratar.
  const { data: user } = useCurrentUser()
  const logout = useLogout()

  return (
    <div className="flex min-h-svh flex-col">
      <header className="flex items-center justify-between border-b px-6 py-3">
        <nav className="flex items-center gap-4">
          <span className="font-heading font-semibold">Dashboard Revenda</span>
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                cn(
                  'text-sm text-muted-foreground hover:text-foreground',
                  isActive && 'font-medium text-foreground',
                )
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="flex items-center gap-3">
          {user && (
            <span className="text-sm text-muted-foreground">
              Logado como <span className="font-medium text-foreground">{user.username}</span>
            </span>
          )}
          <Button
            variant="outline"
            size="sm"
            onClick={() => logout.mutate()}
            disabled={logout.isPending}
          >
            {logout.isPending ? 'Saindo…' : 'Sair'}
          </Button>
        </div>
      </header>

      <main className="flex-1 p-6">
        <Outlet />
      </main>
    </div>
  )
}
