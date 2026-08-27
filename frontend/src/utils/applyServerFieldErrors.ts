import type { FieldPath, FieldValues, UseFormSetError } from 'react-hook-form'

import { ApiError } from '@/services/api'

/**
 * Mapeia o formato de erro de validação da API — {"campo": ["mensagem"]},
 * confirmado consistente em toda a API (Prompt 23) — pros campos certos de
 * um formulário React Hook Form via setError.
 *
 * Client e servidor não são garantidos 100% idênticos (ex. casas decimais
 * de um preço, ver Prompt 30): quando o backend rejeita algo que passou
 * pela validação Zod, é aqui que esse erro chega até o campo certo em vez
 * de virar um "algo deu errado" genérico.
 *
 * Retorna null quando todo erro foi anexado a um campo conhecido do
 * formulário. Retorna uma mensagem quando sobrou algo não mapeável (chave
 * que não é campo nenhum do form, ou a resposta não é um erro de validação
 * 400 no formato esperado) — quem chama decide onde mostrar isso (ex. um
 * alerta no topo do formulário).
 */
export function applyServerFieldErrors<T extends FieldValues>(
  error: unknown,
  setError: UseFormSetError<T>,
  knownFields: readonly FieldPath<T>[],
): string | null {
  if (!(error instanceof ApiError) || error.status !== 400) {
    return error instanceof Error ? error.message : 'Erro inesperado.'
  }

  const body = error.body
  if (!body || typeof body !== 'object' || Array.isArray(body)) {
    return error.message
  }

  const unmatched: string[] = []

  for (const [key, value] of Object.entries(body as Record<string, unknown>)) {
    const message = Array.isArray(value) ? String(value[0]) : String(value)
    const field = knownFields.includes(key as FieldPath<T>) ? (key as FieldPath<T>) : null

    if (field) {
      setError(field, { type: 'server', message })
    } else {
      unmatched.push(message)
    }
  }

  return unmatched.length > 0 ? unmatched.join(' ') : null
}
