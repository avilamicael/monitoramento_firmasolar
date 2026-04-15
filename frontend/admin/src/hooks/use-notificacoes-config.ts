import { useCallback, useEffect, useState } from 'react'
import api from '@/lib/api'
import type {
  CanalNotificacao,
  ConfiguracaoNotificacao,
  ConfiguracaoNotificacaoPayload,
} from '@/types/notificacoes-config'

interface ApiResp<T> { results?: T[] }

function extrairErro(err: unknown, fallback: string): string {
  const e = err as { response?: { status?: number; data?: unknown } }
  if (e?.response?.status === 403) return 'Apenas administradores podem gerenciar notificações.'
  const data = e?.response?.data
  if (data && typeof data === 'object') {
    const detail = (data as Record<string, unknown>).detail
    if (typeof detail === 'string') return detail
    const partes = Object.entries(data as Record<string, unknown>).map(([k, v]) => {
      if (Array.isArray(v)) return `${k}: ${v.join(' ')}`
      return `${k}: ${String(v)}`
    })
    if (partes.length) return partes.join('\n')
  }
  return fallback
}

export function useNotificacoesConfig() {
  const [data, setData] = useState<ConfiguracaoNotificacao[] | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const refetch = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const resp = await api.get<ConfiguracaoNotificacao[] | ApiResp<ConfiguracaoNotificacao>>(
        '/api/notificacoes-config/',
      )
      const results = Array.isArray(resp.data) ? resp.data : (resp.data.results ?? [])
      setData(results)
    } catch (err) {
      setError(extrairErro(err, 'Erro ao carregar configuração.'))
    } finally {
      setLoading(false)
    }
  }, [])

  const criar = useCallback(async (canal: CanalNotificacao, payload: ConfiguracaoNotificacaoPayload) => {
    const resp = await api.post<ConfiguracaoNotificacao>('/api/notificacoes-config/', { canal, ...payload })
    await refetch()
    return resp.data
  }, [refetch])

  const atualizar = useCallback(async (id: number, payload: ConfiguracaoNotificacaoPayload) => {
    const resp = await api.patch<ConfiguracaoNotificacao>(`/api/notificacoes-config/${id}/`, payload)
    await refetch()
    return resp.data
  }, [refetch])

  useEffect(() => {
    void refetch()
  }, [refetch])

  return { data, loading, error, refetch, criar, atualizar, extrairErro }
}
