import { useState, useEffect, useCallback } from 'react'
import api from '@/lib/api'
import type { PotenciaResponse, RankingResponse, MapaUsina } from '@/types/analytics'

const POLL_INTERVAL = 10 * 60 * 1000 // 600_000ms — alinhado com ciclo de coleta do backend

interface UseAnalyticsPotenciaResult {
  data: PotenciaResponse | null
  loading: boolean
  error: string | null
  refetch: () => void
}

export function useAnalyticsPotencia(): UseAnalyticsPotenciaResult {
  const [data, setData] = useState<PotenciaResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetch = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await api.get('/api/analytics/potencia/')
      setData(response.data)
    } catch {
      setError('Erro ao carregar dados de potencia')
    } finally {
      setLoading(false)
    }
  }, []) // sem parametros dinamicos

  useEffect(() => {
    void fetch()
    const timer = setInterval(() => void fetch(), POLL_INTERVAL)
    return () => clearInterval(timer)
  }, [fetch])

  return { data, loading, error, refetch: fetch }
}

interface UseAnalyticsRankingResult {
  data: RankingResponse | null
  loading: boolean
  error: string | null
  refetch: () => void
}

export function useAnalyticsRanking(): UseAnalyticsRankingResult {
  const [data, setData] = useState<RankingResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetch = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await api.get('/api/analytics/ranking-fabricantes/')
      setData(response.data)
    } catch {
      setError('Erro ao carregar ranking de fabricantes')
    } finally {
      setLoading(false)
    }
  }, []) // sem parametros dinamicos

  useEffect(() => {
    void fetch()
    const timer = setInterval(() => void fetch(), POLL_INTERVAL)
    return () => clearInterval(timer)
  }, [fetch])

  return { data, loading, error, refetch: fetch }
}

interface UseAnalyticsMapaResult {
  data: MapaUsina[] | null
  loading: boolean
  error: string | null
  refetch: () => void
}

export function useAnalyticsMapa(): UseAnalyticsMapaResult {
  const [data, setData] = useState<MapaUsina[] | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetch = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await api.get('/api/analytics/mapa/')
      setData(response.data)
    } catch {
      setError('Erro ao carregar mapa de usinas')
    } finally {
      setLoading(false)
    }
  }, []) // sem parametros dinamicos — API retorna array plano sem paginacao

  useEffect(() => {
    void fetch()
    const timer = setInterval(() => void fetch(), POLL_INTERVAL)
    return () => clearInterval(timer)
  }, [fetch])

  return { data, loading, error, refetch: fetch }
}
