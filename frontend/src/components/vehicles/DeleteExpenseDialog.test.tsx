// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen, within } from '@testing-library/react'
import { fireEvent } from '@testing-library/dom'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { DeleteExpenseDialog } from '@/components/vehicles/DeleteExpenseDialog'
import type { VehicleExpense } from '@/types/expense'

const MOCK_EXPENSE: VehicleExpense = {
  id: 'expense-1',
  vehicle: 'vehicle-123',
  date: '2026-08-15',
  category: 'MECHANICAL',
  description: 'Troca de óleo',
  supplier: 'Oficina do Zé',
  amount: '450.00',
  paid: true,
  notes: null,
  deleted_at: null,
  deletion_reason: null,
  created_at: '2026-08-27T00:00:00Z',
  updated_at: '2026-08-27T00:00:00Z',
}

function renderDialog(fetchMock: ReturnType<typeof vi.fn>) {
  vi.stubGlobal('fetch', fetchMock)
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={client}>
      <DeleteExpenseDialog vehicleId="vehicle-123" expense={MOCK_EXPENSE} />
    </QueryClientProvider>,
  )
}

describe('DeleteExpenseDialog', () => {
  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
  })

  it('bloqueia a exclusão sem justificativa preenchida — zero chamada de rede', async () => {
    const fetchMock = vi.fn()
    renderDialog(fetchMock)

    fireEvent.click(screen.getByLabelText('Excluir despesa'))
    const dialog = await screen.findByRole('alertdialog')

    fireEvent.click(within(dialog).getByText('Excluir'))

    expect(fetchMock).not.toHaveBeenCalled()
    within(dialog).getByText('Informe o motivo da exclusão.')
    // continua aberto — não é um "tentou e falhou silenciosamente"
    screen.getByRole('alertdialog')
  })

  it('preenchendo a justificativa e confirmando, dispara o DELETE com deletion_reason no corpo', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 204 }))
    renderDialog(fetchMock)

    fireEvent.click(screen.getByLabelText('Excluir despesa'))
    const dialog = await screen.findByRole('alertdialog')

    fireEvent.change(within(dialog).getByLabelText('Motivo da exclusão'), {
      target: { value: 'Lançamento duplicado por engano' },
    })
    fireEvent.click(within(dialog).getByText('Excluir'))

    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1))

    const [url, options] = fetchMock.mock.calls[0]
    expect(String(url)).toContain('/api/expenses/expense-1/')
    expect(options.method).toBe('DELETE')
    expect(JSON.parse(options.body)).toEqual({
      deletion_reason: 'Lançamento duplicado por engano',
    })
  })
})
