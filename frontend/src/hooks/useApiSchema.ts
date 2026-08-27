import { useQuery } from '@tanstack/react-query'

import { apiFetch } from '@/services/api'
import type { OpenApiSchema } from '@/types/schema'

export function useApiSchema() {
  return useQuery({
    queryKey: ['api-schema'],
    queryFn: () => apiFetch<OpenApiSchema>('/api/schema/?format=json'),
    retry: false,
  })
}
