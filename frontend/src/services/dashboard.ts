import { apiFetch } from '@/services/api'
import type { DashboardSummary } from '@/types/dashboard'

export function fetchDashboardSummary(): Promise<DashboardSummary> {
  return apiFetch<DashboardSummary>('/api/dashboard/summary/')
}
