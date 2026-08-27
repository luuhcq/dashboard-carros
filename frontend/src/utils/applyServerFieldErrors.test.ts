import { describe, expect, it, vi } from 'vitest'

import { ApiError } from '@/services/api'
import { applyServerFieldErrors } from './applyServerFieldErrors'

const knownFields = ['brand', 'purchase_price'] as const

describe('applyServerFieldErrors', () => {
  it('mapeia um erro de campo conhecido pra setError e retorna null (nada sobrou)', () => {
    const setError = vi.fn()
    const error = new ApiError('400 Bad Request', 400, {
      purchase_price: ['Certifique-se de que não haja mais de 2 casas decimais.'],
    })

    const leftover = applyServerFieldErrors(error, setError, knownFields)

    expect(setError).toHaveBeenCalledWith('purchase_price', {
      type: 'server',
      message: 'Certifique-se de que não haja mais de 2 casas decimais.',
    })
    expect(leftover).toBeNull()
  })

  it('mapeia múltiplos campos na mesma resposta', () => {
    const setError = vi.fn()
    const error = new ApiError('400 Bad Request', 400, {
      brand: ['This field is required.'],
      purchase_price: ['purchase_price não pode ser negativo.'],
    })

    applyServerFieldErrors(error, setError, knownFields)

    expect(setError).toHaveBeenCalledTimes(2)
    expect(setError).toHaveBeenCalledWith('brand', {
      type: 'server',
      message: 'This field is required.',
    })
    expect(setError).toHaveBeenCalledWith('purchase_price', {
      type: 'server',
      message: 'purchase_price não pode ser negativo.',
    })
  })

  it('chave que não é campo nenhum do formulário vira mensagem solta, não é descartada', () => {
    const setError = vi.fn()
    const error = new ApiError('400 Bad Request', 400, {
      non_field_errors: ['Algo além de um campo específico deu errado.'],
    })

    const leftover = applyServerFieldErrors(error, setError, knownFields)

    expect(setError).not.toHaveBeenCalled()
    expect(leftover).toBe('Algo além de um campo específico deu errado.')
  })

  it('erro que não é ApiError 400 (ex. rede/500) retorna a mensagem genérica, não tenta mapear campo', () => {
    const setError = vi.fn()
    const error = new ApiError('500 Internal Server Error', 500, { detail: 'erro interno' })

    const leftover = applyServerFieldErrors(error, setError, knownFields)

    expect(setError).not.toHaveBeenCalled()
    expect(leftover).toBe('500 Internal Server Error')
  })

  it('erro de rede (não é ApiError) retorna a mensagem do Error', () => {
    const setError = vi.fn()
    const error = new TypeError('Failed to fetch')

    const leftover = applyServerFieldErrors(error, setError, knownFields)

    expect(setError).not.toHaveBeenCalled()
    expect(leftover).toBe('Failed to fetch')
  })
})
