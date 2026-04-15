import { useCallback, useEffect, useState } from 'react'
import api from '@/lib/api'
import type {
  CredencialProvedor,
  CredencialWritePayload,
  ProvedoresMetaResponse,
} from '@/types/provedores'

interface UseProvedoresResult {
  data: CredencialProvedor[] | null
  meta: ProvedoresMetaResponse | null
  loading: boolean
  error: string | null
  refetch: () => Promise<void>
  criar: (payload: CredencialWritePayload) => Promise<CredencialProvedor>
  atualizar: (id: string, payload: CredencialWritePayload) => Promise<CredencialProvedor>
  remover: (id: string) => Promise<void>
  forcarColeta: (id: string) => Promise<void>
}

function extrairErro(err: unknown, fallback: string): string {
  const e = err as { response?: { status?: number; data?: unknown } }
  if (e?.response?.status === 403) return 'Sem permissão — apenas administradores podem gerenciar provedores.'
  const data = e?.response?.data
  if (data && typeof data === 'object') {
    const detail = (data as Record<string, unknown>).detail
    if (typeof detail === 'string') return detail
    const partes = Object.entries(data as Record<string, unknown>).map(([chave, valor]) => {
      if (Array.isArray(valor)) return `${chave}: ${valor.join(' ')}`
      if (typeof valor === 'object' && valor !== null) return `${chave}: ${JSON.stringify(valor)}`
      return `${chave}: ${String(valor)}`
    })
    if (partes.length) return partes.join('\n')
  }
  return fallback
}

export function useProvedores(): UseProvedoresResult {
  const [data, setData] = useState<CredencialProvedor[] | null>(null)
  const [meta, setMeta] = useState<ProvedoresMetaResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const refetch = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [lista, metaResp] = await Promise.all([
        api.get<CredencialProvedor[] | { results: CredencialProvedor[] }>('/api/provedores/'),
        api.get<ProvedoresMetaResponse>('/api/provedores/meta/'),
      ])
      const payload = lista.data
      const results = Array.isArray(payload) ? payload : payload.results
      setData(results)
      setMeta(metaResp.data)
    } catch (err) {
      setError(extrairErro(err, 'Erro ao carregar provedores'))
    } finally {
      setLoading(false)
    }
  }, [])

  const criar = useCallback(async (payload: CredencialWritePayload) => {
    const resp = await api.post<CredencialProvedor>('/api/provedores/', payload)
    await refetch()
    return resp.data
  }, [refetch])

  const atualizar = useCallback(async (id: string, payload: CredencialWritePayload) => {
    const resp = await api.patch<CredencialProvedor>(`/api/provedores/${id}/`, payload)
    await refetch()
    return resp.data
  }, [refetch])

  const remover = useCallback(async (id: string) => {
    await api.delete(`/api/provedores/${id}/`)
    await refetch()
  }, [refetch])

  const forcarColeta = useCallback(async (id: string) => {
    await api.post(`/api/provedores/${id}/forcar-coleta/`)
  }, [])

  useEffect(() => {
    void refetch()
  }, [refetch])

  return { data, meta, loading, error, refetch, criar, atualizar, remover, forcarColeta }
}

export { extrairErro as extrairErroProvedor }
