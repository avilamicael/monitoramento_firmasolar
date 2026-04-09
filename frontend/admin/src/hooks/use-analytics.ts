import { useState, useEffect, useCallback } from 'react'
import api from '@/lib/api'
import type {
  PotenciaResponse,
  RankingResponse,
  MapaUsina,
  EnergiaResumo,
  AlertasResumo,
  GeracaoDiaria,
} from '@/types/analytics'

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

interface UseEnergiaResumoResult {
  data: EnergiaResumo | null
  loading: boolean
  error: string | null
  refetch: () => void
}

export function useEnergiaResumo(): UseEnergiaResumoResult {
  const [data, setData] = useState<EnergiaResumo | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetch = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await api.get('/api/analytics/energia-resumo/')
      setData(response.data)
    } catch {
      setError('Erro ao carregar resumo de energia')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void fetch()
    const timer = setInterval(() => void fetch(), POLL_INTERVAL)
    return () => clearInterval(timer)
  }, [fetch])

  return { data, loading, error, refetch: fetch }
}

interface UseAlertasResumoResult {
  data: AlertasResumo | null
  loading: boolean
  error: string | null
  refetch: () => void
}

export function useAlertasResumo(): UseAlertasResumoResult {
  const [data, setData] = useState<AlertasResumo | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetch = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await api.get('/api/analytics/alertas-resumo/')
      setData(response.data)
    } catch {
      setError('Erro ao carregar resumo de alertas')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void fetch()
    const timer = setInterval(() => void fetch(), POLL_INTERVAL)
    return () => clearInterval(timer)
  }, [fetch])

  return { data, loading, error, refetch: fetch }
}

interface UseGeracaoDiariaResult {
  data: GeracaoDiaria | null
  loading: boolean
  error: string | null
  refetch: () => void
}

export function useGeracaoDiaria(dias: number = 30): UseGeracaoDiariaResult {
  const [data, setData] = useState<GeracaoDiaria | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetch = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await api.get('/api/analytics/geracao-diaria/', {
        params: { dias },
      })
      setData(response.data)
    } catch {
      setError('Erro ao carregar geracao diaria')
    } finally {
      setLoading(false)
    }
  }, [dias])

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
