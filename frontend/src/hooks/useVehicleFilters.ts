import { useCallback, useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'

import { useDebouncedValue } from '@/hooks/useDebouncedValue'
import type {
  AgingBucket,
  VehicleListParams,
  VehicleOrderingField,
  VehicleStatus,
} from '@/types/vehicle'

const SEARCH_DEBOUNCE_MS = 400

type SoldFilter = 'all' | 'sold' | 'not_sold'
type SortDirection = 'asc' | 'desc' | null

/**
 * Um campo de texto (search/brand/model) cujo valor "comprometido" é o da
 * URL, mas cujo <input> precisa responder a cada tecla sem disparar uma
 * requisição por caractere. `input` é o que a UI mostra; o efeito abaixo só
 * escreve na URL depois do debounce, e só se o valor realmente mudou —
 * sem isso, voltar/avançar no navegador reescreveria a URL em loop.
 */
function useDebouncedSearchParam(
  searchParams: URLSearchParams,
  setSearchParams: ReturnType<typeof useSearchParams>[1],
  key: string,
) {
  const urlValue = searchParams.get(key) ?? ''
  const [input, setInput] = useState(urlValue)
  const debounced = useDebouncedValue(input, SEARCH_DEBOUNCE_MS)

  useEffect(() => {
    const current = searchParams.get(key) ?? ''
    if (debounced === current) return
    setSearchParams(
      (prev) => {
        const next = new URLSearchParams(prev)
        if (debounced) next.set(key, debounced)
        else next.delete(key)
        return next
      },
      { replace: true },
    )
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debounced, key])

  // Muito de fora (voltar/avançar do navegador, "limpar filtros") muda a URL
  // sem passar pelo debounce acima — sincroniza o input de volta nesse caso,
  // mas só quando o valor realmente veio de fora (não do nosso próprio
  // commit, senão entra em loop).
  useEffect(() => {
    const current = searchParams.get(key) ?? ''
    if (current !== debounced && current !== input) {
      setInput(current)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams, key])

  return [input, setInput] as const
}

export function useVehicleFilters() {
  const [searchParams, setSearchParams] = useSearchParams()

  const [searchInput, setSearchInput] = useDebouncedSearchParam(
    searchParams,
    setSearchParams,
    'search',
  )
  const [brandInput, setBrandInput] = useDebouncedSearchParam(
    searchParams,
    setSearchParams,
    'brand',
  )
  const [modelInput, setModelInput] = useDebouncedSearchParam(
    searchParams,
    setSearchParams,
    'model',
  )

  const setParam = useCallback(
    (key: string, value: string | null) => {
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev)
          if (value) next.set(key, value)
          else next.delete(key)
          return next
        },
        { replace: true },
      )
    },
    [setSearchParams],
  )

  const status = (searchParams.get('status') as VehicleStatus) || null
  const agingBucket = (searchParams.get('aging_bucket') as AgingBucket) || null
  const soldFilter: SoldFilter =
    searchParams.get('is_sold') === 'true'
      ? 'sold'
      : searchParams.get('is_sold') === 'false'
        ? 'not_sold'
        : 'all'
  const ordering = searchParams.get('ordering')

  const setStatus = useCallback((value: VehicleStatus | null) => setParam('status', value), [setParam])
  const setAgingBucket = useCallback(
    (value: AgingBucket | null) => setParam('aging_bucket', value),
    [setParam],
  )
  const setSoldFilter = useCallback(
    (value: SoldFilter) =>
      setParam('is_sold', value === 'sold' ? 'true' : value === 'not_sold' ? 'false' : null),
    [setParam],
  )

  const getSortDirection = useCallback(
    (field: VehicleOrderingField): SortDirection => {
      if (ordering === field) return 'asc'
      if (ordering === `-${field}`) return 'desc'
      return null
    },
    [ordering],
  )

  // Ciclo por coluna: nenhum -> asc -> desc -> nenhum. Clicar numa coluna
  // diferente troca a ordenação inteira pra ela (só uma coluna ordenada por
  // vez — é o que ?ordering= da API suporta).
  const toggleSort = useCallback(
    (field: VehicleOrderingField) => {
      const current = getSortDirection(field)
      if (current === null) setParam('ordering', field)
      else if (current === 'asc') setParam('ordering', `-${field}`)
      else setParam('ordering', null)
    },
    [getSortDirection, setParam],
  )

  const clearFilters = useCallback(() => {
    setSearchInput('')
    setBrandInput('')
    setModelInput('')
    setSearchParams(new URLSearchParams(), { replace: true })
  }, [setSearchInput, setBrandInput, setModelInput, setSearchParams])

  const params: VehicleListParams = useMemo(
    () => ({
      status: (searchParams.get('status') as VehicleStatus) || undefined,
      brand: searchParams.get('brand') || undefined,
      model: searchParams.get('model') || undefined,
      aging_bucket: (searchParams.get('aging_bucket') as AgingBucket) || undefined,
      is_sold: searchParams.has('is_sold') ? searchParams.get('is_sold') === 'true' : undefined,
      search: searchParams.get('search') || undefined,
      ordering: ordering || undefined,
    }),
    [searchParams, ordering],
  )

  const hasActiveFilters = [...searchParams.keys()].length > 0

  return {
    params,
    searchInput,
    setSearchInput,
    brandInput,
    setBrandInput,
    modelInput,
    setModelInput,
    status,
    setStatus,
    agingBucket,
    setAgingBucket,
    soldFilter,
    setSoldFilter,
    ordering,
    getSortDirection,
    toggleSort,
    hasActiveFilters,
    clearFilters,
  }
}
