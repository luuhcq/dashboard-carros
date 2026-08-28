// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { VehicleDetailPage } from '@/pages/VehicleDetailPage'
import type { VehicleDetail } from '@/types/vehicle'

function jsonResponse(body: unknown, status: number) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

// Valores reais confirmados via curl contra o backend nos Prompts 32/33/34
// (mesmos veículos usados nas provas ao vivo) — reaproveitados aqui em vez
// de inventados, conforme pedido do prompt.

// Honda Civic LISTED (f3048d6e) — não vendido, com asking_price.
const VEHICLE_NOT_SOLD: VehicleDetail = {
  id: 'f3048d6e-ab8e-49b6-97dc-acd501b5167d',
  internal_code: 'CAR-000070',
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
  notes: 'Revisado no Prompt 31',
  deleted_at: null,
  deletion_reason: null,
  created_at: '2026-08-27T12:48:40.389735-03:00',
  updated_at: '2026-08-27T14:09:04.192275-03:00',
  metrics: {
    total_expenses: '0.00',
    total_cost: '45000.00',
    fipe_percentage_paid: '0.8654',
    fipe_discount: '0.1346',
    projected_profit: '10000.00',
    projected_margin: '0.1818',
    projected_roi: '0.2222',
    profit: null,
    margin: null,
    roi: null,
    days_in_stock: 234,
    aging_bucket: '90+',
    profit_per_day: null,
  },
}

// Honda Civic SOLD (07281d8f) — venda com lucro.
const VEHICLE_SOLD: VehicleDetail = {
  id: '07281d8f-2568-4d7d-aeb2-848b49889387',
  internal_code: 'CAR-000014',
  company: 'company-2',
  brand: 'Honda',
  model: 'Civic',
  version: null,
  manufacture_year: null,
  model_year: null,
  mileage: null,
  plate: null,
  chassis: null,
  color: null,
  status: 'SOLD',
  source: null,
  supplier_name: null,
  purchase_date: '2026-01-05',
  purchase_price: '45000.00',
  fipe_reference_value: null,
  fipe_code: null,
  asking_price: '52000.00',
  sale_date: '2026-02-12',
  sale_price: '49500.00',
  notes: null,
  deleted_at: null,
  deletion_reason: null,
  created_at: '2026-08-25T16:43:30.557993-03:00',
  updated_at: '2026-08-25T16:43:30.766899-03:00',
  metrics: {
    total_expenses: '0.00',
    total_cost: '45000.00',
    fipe_percentage_paid: null,
    fipe_discount: null,
    projected_profit: '7000.00',
    projected_margin: '0.1346',
    projected_roi: '0.1556',
    profit: '4500.00',
    margin: '0.0909',
    roi: '0.1000',
    days_in_stock: 38,
    aging_bucket: '31-45',
    profit_per_day: '118.42',
  },
}

// Fiat Argo (8e8a4340) — sem fipe_reference_value nem asking_price ainda.
const VEHICLE_WITHOUT_PRICES: VehicleDetail = {
  id: '8e8a4340-073b-4e53-b494-104a407cdcbc',
  internal_code: 'CAR-000080',
  company: 'company-3',
  brand: 'Fiat',
  model: 'Argo',
  version: null,
  manufacture_year: null,
  model_year: null,
  mileage: null,
  plate: null,
  chassis: null,
  color: null,
  status: 'PURCHASED',
  source: null,
  supplier_name: null,
  purchase_date: '2026-08-01',
  purchase_price: '30000.00',
  fipe_reference_value: null,
  fipe_code: null,
  asking_price: null,
  sale_date: null,
  sale_price: null,
  notes: null,
  deleted_at: null,
  deletion_reason: null,
  created_at: '2026-08-27T14:36:31.553389-03:00',
  updated_at: '2026-08-27T14:36:31.553392-03:00',
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
    days_in_stock: 26,
    aging_bucket: '16-30',
    profit_per_day: null,
  },
}

/** Localiza o <dd> irmão do <dt> com esse rótulo — mesmo padrão DetailField
 * usado por VehiclePurchaseSection/VehicleResultSection (dt+dd num mesmo
 * div). Evita contar "—" soltos no documento inteiro, que aparecem várias
 * vezes por campo diferente. */
function fieldValue(labelText: string): string {
  const dt = screen.getByText(labelText)
  const dd = dt.parentElement?.querySelector('dd')
  if (!dd) throw new Error(`<dd> não encontrado ao lado do rótulo "${labelText}"`)
  return dd.textContent ?? ''
}

function mockVehicleAndExpenses(
  vehicleResponse: { body: unknown; status: number },
  expenses: unknown[] = [],
) {
  const fetchMock = vi.fn((input: RequestInfo | URL) => {
    const url = String(input)
    if (/\/api\/vehicles\/[^/?]+\/expenses\/$/.test(url)) {
      return Promise.resolve(jsonResponse(expenses, 200))
    }
    if (/\/api\/vehicles\/[^/?]+\/$/.test(url)) {
      return Promise.resolve(jsonResponse(vehicleResponse.body, vehicleResponse.status))
    }
    return Promise.reject(new Error(`fetch inesperado nesse teste: ${url}`))
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

function renderPage(id: string, client?: QueryClient) {
  const queryClient = client ?? new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[`/vehicles/${id}`]}>
        <Routes>
          <Route path="/vehicles/:id" element={<VehicleDetailPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('VehicleDetailPage — composição', () => {
  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
  })

  it('veículo não vendido com asking_price: cabeçalho, compra e bloco projetado juntos, sem bloco realizado', async () => {
    mockVehicleAndExpenses({ body: VEHICLE_NOT_SOLD, status: 200 })

    renderPage(VEHICLE_NOT_SOLD.id)

    // Cabeçalho
    await screen.findByRole('heading', { name: /Honda Civic/ })
    screen.getByText('Anunciado') // VEHICLE_STATUS_LABELS.LISTED

    // Compra
    screen.getByText('Compra')
    expect(fieldValue('Valor de compra')).toBe('R$ 45.000,00')

    // Bloco projetado presente, batendo com o mock (mesmos valores do curl)
    const resultCard = screen.getByText('Resultado').closest('[data-slot="card"]') as HTMLElement
    expect(fieldValue('Preço pedido')).toBe('R$ 55.000,00')
    expect(fieldValue('Lucro projetado')).toBe('R$ 10.000,00')
    expect(fieldValue('Margem projetada')).toBe('18,18%')
    expect(fieldValue('ROI projetado')).toBe('22,22%')

    // Bloco realizado ausente — mutuamente exclusivo com o projetado
    expect(within(resultCard).queryByText('Preço de venda')).toBeNull()
    expect(within(resultCard).queryByText('Lucro realizado')).toBeNull()
    expect(within(resultCard).queryByText('Dias em estoque')).toBeNull()
  })

  it('veículo vendido: bloco realizado presente, bloco projetado ausente', async () => {
    mockVehicleAndExpenses({ body: VEHICLE_SOLD, status: 200 })

    renderPage(VEHICLE_SOLD.id)

    await screen.findByRole('heading', { name: /Honda Civic/ })

    const resultCard = screen.getByText('Resultado').closest('[data-slot="card"]') as HTMLElement
    // Badge "Vendido" reforçando visualmente o bloco realizado (Prompt 34).
    within(resultCard).getByText('Vendido')

    expect(fieldValue('Preço de venda')).toBe('R$ 49.500,00')
    expect(fieldValue('Data da venda')).toBe('12/02/2026')
    expect(fieldValue('Lucro realizado')).toBe('R$ 4.500,00')
    expect(fieldValue('Margem')).toBe('9,09%')
    expect(fieldValue('ROI')).toBe('10,00%')
    expect(fieldValue('Lucro por dia')).toBe('R$ 118,42')
    expect(fieldValue('Dias em estoque')).toContain('38 dias')
    within(resultCard).getByText('31–45 dias')

    // Bloco projetado ausente
    expect(within(resultCard).queryByText('Preço pedido')).toBeNull()
    expect(within(resultCard).queryByText('Lucro projetado')).toBeNull()
  })

  it('veículo sem fipe_reference_value/asking_price: campos calculados mostram "—", sem NaN', async () => {
    mockVehicleAndExpenses({ body: VEHICLE_WITHOUT_PRICES, status: 200 })

    renderPage(VEHICLE_WITHOUT_PRICES.id)

    await screen.findByRole('heading', { name: /Fiat Argo/ })

    // Compra — dependentes de fipe_reference_value
    expect(fieldValue('FIPE de referência')).toBe('—')
    expect(fieldValue('% FIPE pago')).toBe('—')
    expect(fieldValue('Desconto sobre FIPE')).toBe('—')

    // Resultado — projetado, dependente de asking_price
    expect(fieldValue('Preço pedido')).toBe('—')
    expect(fieldValue('Lucro projetado')).toBe('—')
    expect(fieldValue('Margem projetada')).toBe('—')
    expect(fieldValue('ROI projetado')).toBe('—')

    expect(document.body.textContent).not.toMatch(/NaN/)
  })

  it('UUID inexistente: estado "não encontrado" distinto de erro de rede, sem retry (404 não tenta de novo)', async () => {
    const fetchMock = mockVehicleAndExpenses({
      body: { detail: 'Not found.' },
      status: 404,
    })

    // Sem defaultOptions.retry:false aqui de propósito — useVehicle já
    // define seu próprio `retry` (pula retry em 404); esse teste teria que
    // falhar se essa lógica de fato regredisse, não só porque o client
    // global desativou retry por fora.
    renderPage('00000000-0000-0000-0000-000000000000', new QueryClient())

    await screen.findByText('Veículo não encontrado.')
    // Distinto da mensagem de erro de rede/servidor (VehicleDetailPage
    // trata os dois casos de forma diferente).
    expect(screen.queryByText('Não foi possível carregar este veículo.')).toBeNull()
    // Nenhum botão de "tentar de novo" — 404 não é transitório.
    expect(screen.queryByRole('button', { name: /Tentar de novo/ })).toBeNull()

    const vehicleDetailCalls = fetchMock.mock.calls.filter(([input]) =>
      /\/api\/vehicles\/[^/?]+\/$/.test(String(input)),
    )
    expect(vehicleDetailCalls).toHaveLength(1)
  })
})
