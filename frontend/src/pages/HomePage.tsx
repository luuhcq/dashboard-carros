import { ApiStatus } from '@/components/ApiStatus'

export function HomePage() {
  return (
    <main className="flex min-h-svh flex-col items-center justify-center gap-4 p-8">
      <h1 className="text-2xl font-semibold">Dashboard Revenda</h1>
      <ApiStatus />
    </main>
  )
}
