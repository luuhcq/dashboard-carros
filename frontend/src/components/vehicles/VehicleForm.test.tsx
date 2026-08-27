// @vitest-environment jsdom
import { cleanup, render, screen } from '@testing-library/react'
import { fireEvent } from '@testing-library/dom'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { VehicleForm } from '@/components/vehicles/VehicleForm'
import { ApiError } from '@/services/api'

// Mesmos valores do veículo real usado na prova ao vivo do Prompt 31 (Honda
// Civic CAR-000070) — strings, porque é isso que VehicleEditPage manda como
// defaultValues (mapeados de VehicleDetail, ver vehicleDetailToFormDefaults).
const DEFAULT_VALUES = {
  brand: 'Honda',
  model: 'Civic',
  version: 'EXL 2.0',
  manufacture_year: '',
  model_year: '2022',
  mileage: '32000',
  plate: '',
  chassis: '',
  color: '',
  source: '',
  supplier_name: '',
  purchase_date: '2026-01-05',
  purchase_price: '45000.00',
  fipe_reference_value: '52000.00',
  fipe_code: '',
  notes: '',
}

function inputValue(label: string): string {
  return (screen.getByLabelText(label) as HTMLInputElement | HTMLTextAreaElement).value
}

function renderEditForm(onSubmit = vi.fn().mockResolvedValue(undefined)) {
  render(
    <VehicleForm
      mode="edit"
      defaultValues={DEFAULT_VALUES}
      pricingInfo={{ askingPrice: '55000.00', salePrice: null }}
      isSubmitting={false}
      submitLabel="Salvar alterações"
      onSubmit={onSubmit}
    />,
  )
  return onSubmit
}

describe('VehicleForm — modo edit', () => {
  afterEach(() => {
    cleanup()
  })

  it('pré-preenche os campos a partir de defaultValues (dados do veículo)', () => {
    renderEditForm()

    expect(inputValue('Marca')).toBe('Honda')
    expect(inputValue('Modelo')).toBe('Civic')
    expect(inputValue('Versão')).toBe('EXL 2.0')
    expect(inputValue('Ano modelo')).toBe('2022')
    expect(inputValue('Quilometragem')).toBe('32000')
    expect(inputValue('Data da compra')).toBe('2026-01-05')
    expect(inputValue('Preço de compra')).toBe('45000.00')
    expect(inputValue('Valor de referência')).toBe('52000.00')
  })

  it('mostra asking_price/sale_price como painel somente-leitura, sem input associado a esses campos', () => {
    renderEditForm()

    screen.getByText('Preço de venda') // título do painel
    screen.getByText('R$ 55.000,00') // asking_price formatado
    screen.getByText('—') // sale_price null
    screen.getByText(
      'Esses valores não são editados por aqui. Gerencie o preço pela página de detalhe do veículo.',
    )

    // nenhum campo do formulário existe pra esses dois — nem desabilitado,
    // nem escondido: eles simplesmente não fazem parte do schema/JSX.
    expect(document.getElementById('asking_price')).toBeNull()
    expect(document.getElementById('sale_price')).toBeNull()
    const allFieldIds = [...document.querySelectorAll('input, textarea')].map((el) => el.id)
    expect(allFieldIds).not.toContain('asking_price')
    expect(allFieldIds).not.toContain('sale_price')
  })

  it('envia só o campo alterado no payload — PATCH parcial de verdade (dirtyFields)', async () => {
    const onSubmit = renderEditForm()

    fireEvent.change(screen.getByLabelText('Observações'), {
      target: { value: 'Revisado no Prompt 31' },
    })
    fireEvent.click(screen.getByText('Salvar alterações'))

    await vi.waitFor(() => expect(onSubmit).toHaveBeenCalledTimes(1))
    expect(onSubmit).toHaveBeenCalledWith({ notes: 'Revisado no Prompt 31' })
  })

  it('reverter um campo pro valor original exclui esse campo do payload (caso validado manualmente no Prompt 31)', async () => {
    const onSubmit = renderEditForm()

    const priceField = screen.getByLabelText('Preço de compra')
    fireEvent.change(priceField, { target: { value: '999999' } })
    fireEvent.change(priceField, { target: { value: '45000.00' } }) // volta pro valor original

    fireEvent.change(screen.getByLabelText('Observações'), {
      target: { value: 'Só isso mudou' },
    })
    fireEvent.click(screen.getByText('Salvar alterações'))

    await vi.waitFor(() => expect(onSubmit).toHaveBeenCalledTimes(1))
    // purchase_price NÃO aparece no payload — RHF não considera "sujo" um
    // campo cujo valor atual voltou a bater com o original, mesmo tendo
    // sido tocado no meio do caminho.
    expect(onSubmit).toHaveBeenCalledWith({ notes: 'Só isso mudou' })
  })

  it('erro de validação do backend aparece no campo certo (mesmo padrão do Prompt 30)', async () => {
    const onSubmit = vi.fn().mockRejectedValue(
      new ApiError('400 Bad Request', 400, {
        purchase_price: ['Certifique-se de que não haja mais de 2 casas decimais.'],
      }),
    )
    renderEditForm(onSubmit)

    fireEvent.change(screen.getByLabelText('Preço de compra'), {
      target: { value: '45000.999' },
    })
    fireEvent.click(screen.getByText('Salvar alterações'))

    await screen.findByText('Certifique-se de que não haja mais de 2 casas decimais.')
  })
})
