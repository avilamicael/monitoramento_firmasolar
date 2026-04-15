import { useEffect, useState } from 'react'
import { toast } from 'sonner'
import { Loader2Icon, SaveIcon } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Skeleton } from '@/components/ui/skeleton'
import { useConfiguracoes } from '@/hooks/use-configuracoes'
import type { ConfiguracaoSistemaUpdate } from '@/types/configuracoes'

interface FormState {
  dias_sem_comunicacao_pausar: string
  meses_garantia_padrao: string
  dias_aviso_garantia_proxima: string
  dias_aviso_garantia_urgente: string
}

const VALORES_INICIAIS: FormState = {
  dias_sem_comunicacao_pausar: '',
  meses_garantia_padrao: '',
  dias_aviso_garantia_proxima: '',
  dias_aviso_garantia_urgente: '',
}

function extrairErroApi(err: unknown): string {
  const e = err as { response?: { status?: number; data?: Record<string, unknown> } }
  if (e?.response?.status === 403) return 'Sem permissão — apenas administradores podem alterar configurações.'
  const data = e?.response?.data
  if (data && typeof data === 'object') {
    const campos = Object.values(data)
      .flatMap((v) => (Array.isArray(v) ? v : [String(v)]))
      .join(' ')
    if (campos) return campos
  }
  return 'Erro ao salvar configurações'
}

export function ConfiguracoesPage() {
  const { data, loading, error, saving, atualizar } = useConfiguracoes()
  const [form, setForm] = useState<FormState>(VALORES_INICIAIS)

  useEffect(() => {
    if (!data) return
    setForm({
      dias_sem_comunicacao_pausar: String(data.dias_sem_comunicacao_pausar),
      meses_garantia_padrao: String(data.meses_garantia_padrao),
      dias_aviso_garantia_proxima: String(data.dias_aviso_garantia_proxima),
      dias_aviso_garantia_urgente: String(data.dias_aviso_garantia_urgente),
    })
  }, [data])

  function handleChange(campo: keyof FormState) {
    return (e: React.ChangeEvent<HTMLInputElement>) => {
      setForm((prev) => ({ ...prev, [campo]: e.target.value }))
    }
  }

  function validar(): ConfiguracaoSistemaUpdate | null {
    const campos: (keyof FormState)[] = [
      'dias_sem_comunicacao_pausar',
      'meses_garantia_padrao',
      'dias_aviso_garantia_proxima',
      'dias_aviso_garantia_urgente',
    ]
    const valores: Record<string, number> = {}
    for (const campo of campos) {
      const valor = Number(form[campo])
      if (!Number.isInteger(valor) || valor < 1) {
        toast.error(`O campo "${campo}" precisa ser um inteiro maior que zero.`)
        return null
      }
      valores[campo] = valor
    }
    if (valores.dias_aviso_garantia_urgente >= valores.dias_aviso_garantia_proxima) {
      toast.error('O aviso urgente precisa ser menor que o aviso prévio.')
      return null
    }
    return valores as unknown as ConfiguracaoSistemaUpdate
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const payload = validar()
    if (!payload) return
    try {
      await atualizar(payload)
      toast.success('Configurações salvas.')
    } catch (err) {
      toast.error(extrairErroApi(err))
    }
  }

  if (loading) {
    return (
      <Card className="max-w-2xl">
        <CardHeader>
          <CardTitle>Configurações</CardTitle>
          <CardDescription>Carregando...</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <Skeleton className="h-9 w-full" />
          <Skeleton className="h-9 w-full" />
          <Skeleton className="h-9 w-full" />
          <Skeleton className="h-9 w-full" />
        </CardContent>
      </Card>
    )
  }

  if (error) {
    return (
      <Card className="max-w-2xl">
        <CardHeader>
          <CardTitle>Configurações</CardTitle>
          <CardDescription className="text-destructive">{error}</CardDescription>
        </CardHeader>
      </Card>
    )
  }

  return (
    <Card className="max-w-2xl">
      <CardHeader>
        <CardTitle>Configurações do Sistema</CardTitle>
        <CardDescription>
          Parâmetros globais que afetam a coleta de dados e a geração de alertas. As mudanças passam a valer
          no próximo ciclo de coleta.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="space-y-2">
            <Label htmlFor="dias_sem_comunicacao_pausar">Dias sem comunicação até pausar coleta</Label>
            <Input
              id="dias_sem_comunicacao_pausar"
              type="number"
              min={1}
              value={form.dias_sem_comunicacao_pausar}
              onChange={handleChange('dias_sem_comunicacao_pausar')}
              required
            />
            <p className="text-xs text-muted-foreground">
              Usinas sem snapshot há mais deste número de dias são automaticamente desativadas.
              Para retomar, abra a página da usina e clique em "Reativar coleta".
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="meses_garantia_padrao">Meses de garantia padrão</Label>
            <Input
              id="meses_garantia_padrao"
              type="number"
              min={1}
              value={form.meses_garantia_padrao}
              onChange={handleChange('meses_garantia_padrao')}
              required
            />
            <p className="text-xs text-muted-foreground">
              Duração da garantia criada automaticamente ao registrar uma usina pela primeira vez.
              Só afeta usinas registradas após a mudança.
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="dias_aviso_garantia_proxima">Aviso prévio de garantia (dias)</Label>
            <Input
              id="dias_aviso_garantia_proxima"
              type="number"
              min={2}
              value={form.dias_aviso_garantia_proxima}
              onChange={handleChange('dias_aviso_garantia_proxima')}
              required
            />
            <p className="text-xs text-muted-foreground">
              Quando a garantia estiver a este número de dias ou menos do fim, cria alerta nível "aviso".
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="dias_aviso_garantia_urgente">Aviso urgente de garantia (dias)</Label>
            <Input
              id="dias_aviso_garantia_urgente"
              type="number"
              min={1}
              value={form.dias_aviso_garantia_urgente}
              onChange={handleChange('dias_aviso_garantia_urgente')}
              required
            />
            <p className="text-xs text-muted-foreground">
              Escala o alerta para nível "importante" quando a garantia estiver a este número de dias ou menos do fim.
              Precisa ser menor que o aviso prévio.
            </p>
          </div>

          <div className="flex items-center justify-between pt-2">
            {data?.atualizado_em && (
              <p className="text-xs text-muted-foreground">
                Última atualização: {new Date(data.atualizado_em).toLocaleString('pt-BR')}
              </p>
            )}
            <Button type="submit" disabled={saving}>
              {saving ? <Loader2Icon className="size-4 animate-spin" /> : <SaveIcon className="size-4" />}
              Salvar
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  )
}
