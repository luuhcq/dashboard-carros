// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen, within } from '@testing-library/react'
import { fireEvent } from '@testing-library/dom'
import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest'

import { AddExpenseDialog } from '@/components/vehicles/AddExpenseDialog'

function jsonResponse(body: unknown, status: number) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

beforeAll(() => {
  // Radix Select (campo Categoria) e Checkbox (campo Pago) chamam essas
  // APIs de layout/ponteiro que jsdom não implementa — confirmado rodando
  // sem os polyfills antes de escrever isso (TypeError: scrollIntoView is
  // not a function; depois, ReferenceError: ResizeObserver is not defined,
  // vindo do Checkbox via @radix-ui/react-use-size).
  Element.prototype.scrollIntoView = () => {}
  Element.prototype.hasPointerCapture = () => false
  Element.prototype.releasePointerCapture = () => {}
  Element.prototype.setPointerCapture = () => {}
  globalThis.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
})

function renderDialog(fetchMock: ReturnType<typeof vi.fn>) {
  vi.stubGlobal('fetch', fetchMock)
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={client}>
      <AddExpenseDialog vehicleId="vehicle-123" />
    </QueryClientProvider>,
  )
}

describe('AddExpenseDialog', () => {
  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
  })

  it('submissão válida chama a mutação com o payload certo, sem vehicle no corpo (injetado da URL)', async () => {
    // Regressão: category sem defaultValue causava "Select is changing from
    // uncontrolled to controlled" (React valida isso via console.error).
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse(
        {
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
        },
        201,
      ),
    )
    renderDialog(fetchMock)

    // abre o dialog — só um "Adicionar despesa" na tela nesse ponto
    fireEvent.click(screen.getByText('Adicionar despesa'))
    const dialog = await screen.findByRole('dialog')

    fireEvent.change(within(dialog).getByLabelText('Data'), {
      target: { value: '2026-08-15' },
    })

    fireEvent.click(within(dialog).getByLabelText('Categoria'))
    // Radix também renderiza um <select> nativo oculto (compatibilidade de
    // formulário/autofill) com as mesmas opções como texto — sem escopar
    // pro listbox aberto, "Mecânica" bate em dois elementos.
    const listbox = await screen.findByRole('listbox')
    fireEvent.click(within(listbox).getByText('Mecânica'))

    fireEvent.change(within(dialog).getByLabelText('Descrição'), {
      target: { value: 'Troca de óleo' },
    })
    fireEvent.change(within(dialog).getByLabelText('Fornecedor'), {
      target: { value: 'Oficina do Zé' },
    })
    fireEvent.change(within(dialog).getByLabelText('Valor'), {
      target: { value: '450.00' },
    })
    fireEvent.click(within(dialog).getByLabelText('Pago'))

    fireEvent.click(within(dialog).getByRole('button', { name: 'Adicionar despesa' }))

    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1))

    const [url, options] = fetchMock.mock.calls[0]
    expect(String(url)).toContain('/api/vehicles/vehicle-123/expenses/')
    expect(options.method).toBe('POST')

    const sentBody = JSON.parse(options.body)
    expect(sentBody).toEqual({
      date: '2026-08-15',
      category: 'MECHANICAL',
      description: 'Troca de óleo',
      supplier: 'Oficina do Zé',
      amount: 450,
      paid: true,
    })
    // vehicle não é campo do formulário — read_only, injetado da URL pelo
    // backend (perform_create), nunca vem do client.
    expect(sentBody).not.toHaveProperty('vehicle')

    for (const call of consoleErrorSpy.mock.calls) {
      expect(String(call[0])).not.toContain('changing from uncontrolled to controlled')
      expect(String(call[0])).not.toContain('changing from controlled to uncontrolled')
    }
    consoleErrorSpy.mockRestore()
  })
})
