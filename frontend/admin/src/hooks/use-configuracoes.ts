import { useCallback, useEffect, useState } from 'react'
import api from '@/lib/api'
import type { ConfiguracaoSistema, ConfiguracaoSistemaUpdate } from '@/types/configuracoes'

interface UseConfiguracoesResult {
  data: ConfiguracaoSistema | null
  loading: boolean
  error: string | null
  saving: boolean
  refetch: () => Promise<void>
  atualizar: (payload: ConfiguracaoSistemaUpdate) => Promise<ConfiguracaoSistema>
}

function extrairErro(err: unknown, fallback: string): string {
  const e = err as { response?: { status?: number; data?: Record<string, unknown> } }
  if (e?.response?.status === 403) return 'Você não tem permissão para acessar as configurações.'
  const data = e?.response?.data
  if (data && typeof data === 'object') {
    const campos = Object.entries(data)
      .map(([chave, valor]) => {
        const msg = Array.isArray(valor) ? valor.join(' ') : String(valor)
        return `${chave}: ${msg}`
      })
      .join('\n')
    if (campos) return campos
  }
  return fallback
}

export function useConfiguracoes(): UseConfiguracoesResult {
  const [data, setData] = useState<ConfiguracaoSistema | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const refetch = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await api.get<ConfiguracaoSistema>('/api/configuracoes/')
      setData(response.data)
    } catch (err) {
      setError(extrairErro(err, 'Erro ao carregar configurações'))
    } finally {
      setLoading(false)
    }
  }, [])

  const atualizar = useCallback(async (payload: ConfiguracaoSistemaUpdate) => {
    setSaving(true)
    try {
      const response = await api.put<ConfiguracaoSistema>('/api/configuracoes/', payload)
      setData(response.data)
      return response.data
    } finally {
      setSaving(false)
    }
  }, [])

  useEffect(() => {
    void refetch()
  }, [refetch])

  return { data, loading, error, saving, refetch, atualizar }
}
