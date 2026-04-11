import { useState, useEffect, useCallback } from 'react'
import api from '@/lib/api'
import type { AlertaDetalhe, EstadoAlerta, NivelAlerta, OrigemAlerta, PaginatedAlertas } from '@/types/alertas'

interface UseAlertasParams {
  estado?: EstadoAlerta
  nivel?: NivelAlerta
  origem?: OrigemAlerta
  provedor?: string
  categoria?: string
  busca?: string
  usina?: string
  page?: number
}

interface UseAlertasResult {
  data: PaginatedAlertas | null
  loading: boolean
  error: string | null
  refetch: () => void
}

export function useAlertas(params: UseAlertasParams = {}): UseAlertasResult {
  const [data, setData] = useState<PaginatedAlertas | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // eslint-disable-next-line react-hooks/exhaustive-deps
  const fetch = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await api.get('/api/alertas/', { params })
      setData(response.data)
    } catch {
      setError('Erro ao carregar alertas')
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

interface UseAlertaResult {
  data: AlertaDetalhe | null
  loading: boolean
  error: string | null
  refetch: () => void
}

export function useAlerta(id: string): UseAlertaResult {
  const [data, setData] = useState<AlertaDetalhe | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetch = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await api.get(`/api/alertas/${id}/`)
      setData(response.data)
    } catch {
      setError('Erro ao carregar alerta')
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => {
    void fetch()
  }, [fetch])

  return { data, loading, error, refetch: fetch }
}
