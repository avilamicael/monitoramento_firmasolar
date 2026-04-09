import { useState, useEffect, useCallback } from 'react'
import api from '@/lib/api'
import type { UsinaDetalhe, PaginatedUsinas, StatusGarantia } from '@/types/usinas'

interface UseUsinasParams {
  provedor?: string
  ativo?: boolean
  status_garantia?: StatusGarantia
  page?: number
}

interface UseUsinasResult {
  data: PaginatedUsinas | null
  loading: boolean
  error: string | null
  refetch: () => void
}

export function useUsinas(params: UseUsinasParams = {}): UseUsinasResult {
  const [data, setData] = useState<PaginatedUsinas | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // eslint-disable-next-line react-hooks/exhaustive-deps
  const fetch = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await api.get('/api/usinas/', { params })
      setData(response.data)
    } catch {
      setError('Erro ao carregar usinas')
    } finally {
      setLoading(false)
    }
  // JSON.stringify evita loop infinito quando params e objeto literal recriado a cada render
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [JSON.stringify(params)])

  useEffect(() => {
    void fetch()
  }, [fetch])

  return { data, loading, error, refetch: fetch }
}

interface UseUsinaResult {
  data: UsinaDetalhe | null
  loading: boolean
  error: string | null
  refetch: () => void
}

export function useUsina(id: string): UseUsinaResult {
  const [data, setData] = useState<UsinaDetalhe | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetch = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await api.get(`/api/usinas/${id}/`)
      setData(response.data)
    } catch {
      setError('Erro ao carregar usina')
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => {
    void fetch()
  }, [fetch])

  return { data, loading, error, refetch: fetch }
}
