import { useState, useEffect, useCallback } from 'react'
import api from '@/lib/api'
import type { PaginatedGarantias } from '@/types/garantias'

interface UseGarantiasParams {
  filtro?: 'ativas' | 'vencendo' | 'vencidas'
  page?: number
}

interface UseGarantiasResult {
  data: PaginatedGarantias | null
  loading: boolean
  error: string | null
  refetch: () => void
}

export function useGarantias(params: UseGarantiasParams = {}): UseGarantiasResult {
  const [data, setData] = useState<PaginatedGarantias | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // eslint-disable-next-line react-hooks/exhaustive-deps
  const fetch = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await api.get('/api/garantias/', { params })
      setData(response.data)
    } catch {
      setError('Erro ao carregar garantias')
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
