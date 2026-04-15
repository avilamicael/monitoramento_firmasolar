import { useCallback, useEffect, useRef, useState } from 'react'
import api from '@/lib/api'
import type { PaginatedNotificacoes } from '@/types/notificacoes'

const POLLING_MS = 60_000

interface UseNotificacoesOpts {
  apenasNaoLidas?: boolean
  page?: number
}

export function useNotificacoes({ apenasNaoLidas = false, page = 1 }: UseNotificacoesOpts = {}) {
  const [data, setData] = useState<PaginatedNotificacoes | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const refetch = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const params: Record<string, string | number> = { page }
      if (apenasNaoLidas) params.apenas_nao_lidas = 'true'
      const resp = await api.get<PaginatedNotificacoes>('/api/notificacoes/', { params })
      setData(resp.data)
    } catch {
      setError('Erro ao carregar notificações')
    } finally {
      setLoading(false)
    }
  }, [apenasNaoLidas, page])

  const marcarLida = useCallback(async (id: string) => {
    await api.post(`/api/notificacoes/${id}/marcar-lida/`)
    await refetch()
  }, [refetch])

  const marcarTodasLidas = useCallback(async () => {
    await api.post('/api/notificacoes/marcar-todas-lidas/')
    await refetch()
  }, [refetch])

  useEffect(() => {
    void refetch()
  }, [refetch])

  return { data, loading, error, refetch, marcarLida, marcarTodasLidas }
}

/**
 * Hook para o contador de não lidas no sino do header.
 * Faz polling leve a cada 60s via endpoint /nao-lidas-count/.
 */
export function useNotificacoesCount() {
  const [count, setCount] = useState(0)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const buscar = useCallback(async () => {
    try {
      const resp = await api.get<{ count: number }>('/api/notificacoes/nao-lidas-count/')
      setCount(resp.data.count)
    } catch {
      // Falha silenciosa: evita spam de toasts a cada poll
    }
  }, [])

  useEffect(() => {
    void buscar()
    timerRef.current = setInterval(() => { void buscar() }, POLLING_MS)
    return () => {
      if (timerRef.current) clearInterval(timerRef.current)
    }
  }, [buscar])

  return { count, refetch: buscar }
}
