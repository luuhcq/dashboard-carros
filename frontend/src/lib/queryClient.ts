import { QueryClient } from '@tanstack/react-query'

/**
 * Instância única, importada tanto pelo QueryClientProvider (main.tsx)
 * quanto por código fora de componentes React que precisa mexer no cache
 * (o listener de 401 em services/auth.ts) — por isso não é criada inline
 * dentro de um componente.
 */
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Dado como listagem de veículos muda pouco durante o uso normal da
      // tela; 1 minuto evita refetch a cada foco de janela/troca de aba sem
      // deixar a UI visivelmente desatualizada. Telas com necessidade
      // diferente (ex. dado que muda a cada poucos segundos) sobrescrevem
      // staleTime por query.
      staleTime: 60_000,
      retry: 1,
    },
  },
})
