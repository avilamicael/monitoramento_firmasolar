import { useCallback, useEffect, useState } from 'react'
import api from '@/lib/api'
import type { Usuario, UsuarioWrite } from '@/types/usuarios'

interface ApiResp<T> { results?: T[] }

export function useUsuarios() {
  const [data, setData] = useState<Usuario[] | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const refetch = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const resp = await api.get<Usuario[] | ApiResp<Usuario>>('/api/usuarios/')
      const results = Array.isArray(resp.data) ? resp.data : (resp.data.results ?? [])
      setData(results)
    } catch {
      setError('Erro ao carregar usuários')
    } finally {
      setLoading(false)
    }
  }, [])

  const criar = useCallback(async (payload: UsuarioWrite) => {
    const resp = await api.post<Usuario>('/api/usuarios/', payload)
    await refetch()
    return resp.data
  }, [refetch])

  const atualizar = useCallback(async (id: number, payload: Partial<UsuarioWrite>) => {
    const resp = await api.patch<Usuario>(`/api/usuarios/${id}/`, payload)
    await refetch()
    return resp.data
  }, [refetch])

  const remover = useCallback(async (id: number) => {
    await api.delete(`/api/usuarios/${id}/`)
    await refetch()
  }, [refetch])

  useEffect(() => {
    void refetch()
  }, [refetch])

  return { data, loading, error, refetch, criar, atualizar, remover }
}

export function extrairErroUsuario(err: unknown, fallback: string): string {
  const e = err as { response?: { status?: number; data?: unknown } }
  if (e?.response?.status === 403) return 'Sem permissão para esta ação.'
  if (e?.response?.status === 400) {
    const data = e.response.data
    if (data && typeof data === 'object') {
      const detail = (data as Record<string, unknown>).detail
      if (typeof detail === 'string') return detail
      const partes = Object.entries(data as Record<string, unknown>).map(([k, v]) => {
        if (Array.isArray(v)) return `${k}: ${v.join(' ')}`
        return `${k}: ${String(v)}`
      })
      if (partes.length) return partes.join('\n')
    }
  }
  return fallback
}
