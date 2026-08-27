// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { VehicleExpensesSection } from '@/components/vehicles/VehicleExpensesSection'
import type { VehicleExpense } from '@/types/expense'
import type { VehicleDetail } from '@/types/vehicle'

function jsonResponse(body: unknown, status: number) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

function makeVehicleDetail(overrides: Partial<VehicleDetail> = {}): VehicleDetail {
  return {
    id: 'vehicle-123',
    internal_code: 'CAR-000123',
    company: 'company-1',
    brand: 'Honda',
    model: 'Civic',
    version: 'EXL 2.0',
    manufacture_year: null,
    model_year: 2022,
    mileage: 32000,
    plate: null,
    chassis: null,
    color: null,
    status: 'LISTED',
    source: null,
    supplier_name: null,
    purchase_date: '2026-01-05',
    purchase_price: '45000.00',
    fipe_reference_value: '52000.00',
    fipe_code: null,
    asking_price: '55000.00',
    sale_date: null,
    sale_price: null,
    notes: null,
    deleted_at: null,
    deletion_reason: null,
    created_at: '2026-01-05T00:00:00Z',
    updated_at: '2026-01-05T00:00:00Z',
    metrics: {
      total_expenses: '0.00',
      total_cost: '45000.00',
      fipe_percentage_paid: null,
      fipe_discount: null,
      projected_profit: null,
      projected_margin: null,
      projected_roi: null,
      profit: null,
      margin: null,
      roi: null,
      days_in_stock: 0,
      aging_bucket: '0-15',
      profit_per_day: null,
    },
    ...overrides,
  }
}

function makeExpense(overrides: Partial<VehicleExpense> = {}): VehicleExpense {
  return {
    id: 'expense-1',
    vehicle: 'vehicle-123',
    date: '2026-01-10',
    category: 'MECHANICAL',
    description: 'Troca de óleo',
    supplier: 'Oficina do Zé',
    amount: '100.00',
    paid: true,
    notes: null,
    deleted_at: null,
    deletion_reason: null,
    created_at: '2026-01-10T00:00:00Z',
    updated_at: '2026-01-10T00:00:00Z',
    ...overrides,
  }
}

function renderSection(vehicle: VehicleDetail, fetchMock: ReturnType<typeof vi.fn>) {
  vi.stubGlobal('fetch', fetchMock)
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={client}>
      <VehicleExpensesSection vehicle={vehicle} />
    </QueryClientProvider>,
  )
}

describe('VehicleExpensesSection', () => {
  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
  })

  it('renderiza a lista de despesas a partir do mock', async () => {
    const expenses = [
      makeExpense({
        id: 'expense-1',
        date: '2026-01-10',
        description: 'Troca de óleo',
        supplier: 'Oficina do Zé',
        amount: '100.00',
        paid: true,
      }),
      makeExpense({
        id: 'expense-2',
        category: 'DOCUMENTATION',
        date: '2026-01-12',
        description: 'Transferência',
        supplier: 'Despachante',
        amount: '350.00',
        paid: false,
      }),
    ]
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(expenses, 200))
    renderSection(makeVehicleDetail(), fetchMock)

    await screen.findByText('Troca de óleo')
    screen.getByText('Oficina do Zé')
    screen.getByText('R$ 100,00')
    screen.getByText('Pago')

    screen.getByText('Transferência')
    screen.getByText('Despachante')
    screen.getByText('R$ 350,00')
    screen.getByText('Não pago')
  })

  it('mostra estado vazio apropriado quando não há despesas, sem erro nem tabela quebrada', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse([], 200))
    const vehicle = makeVehicleDetail({
      metrics: {
        total_expenses: '0.00',
        total_cost: '30000.00',
        fipe_percentage_paid: null,
        fipe_discount: null,
        projected_profit: null,
        projected_margin: null,
        projected_roi: null,
        profit: null,
        margin: null,
        roi: null,
        days_in_stock: 5,
        aging_bucket: '0-15',
        profit_per_day: null,
      },
    })
    renderSection(vehicle, fetchMock)

    await screen.findByText('Nenhuma despesa registrada.')
    screen.getByText('R$ 0,00')
    screen.getByText('R$ 30.000,00')
  })

  it('rodapé usa total_cost/total_expenses de metrics, não a soma local da lista (mock deliberadamente divergente)', async () => {
    // Soma real da lista abaixo seria 100 + 200 = 300.00 — deliberadamente
    // diferente de metrics, pra provar que o rodapé não recalcula.
    const expenses = [
      makeExpense({ id: 'expense-1', amount: '100.00' }),
      makeExpense({ id: 'expense-2', amount: '200.00' }),
    ]
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(expenses, 200))
    const vehicle = makeVehicleDetail({
      metrics: {
        total_expenses: '999.99',
        total_cost: '5000.00',
        fipe_percentage_paid: null,
        fipe_discount: null,
        projected_profit: null,
        projected_margin: null,
        projected_roi: null,
        profit: null,
        margin: null,
        roi: null,
        days_in_stock: 10,
        aging_bucket: '0-15',
        profit_per_day: null,
      },
    })
    renderSection(vehicle, fetchMock)

    await screen.findByText('R$ 999,99')
    screen.getByText('R$ 5.000,00')
    // a soma "certa" da lista (300,00) não deveria aparecer em lugar nenhum
    // do rodapé — só nas linhas individuais da tabela.
    expect(screen.queryByText('R$ 300,00')).toBeNull()
  })
})
