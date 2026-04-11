import { useParams, useNavigate } from 'react-router'
import { ArrowLeftIcon } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { AlertaEstadoForm } from '@/components/alertas/AlertaEstadoForm'
import { useAlerta } from '@/hooks/use-alertas'
import type { NivelAlerta, EstadoAlerta } from '@/types/alertas'

const NIVEL_CONFIG: Record<NivelAlerta, { label: string; className?: string; variant?: 'destructive' | 'secondary' | 'outline' }> = {
  critico: { label: 'Critico', variant: 'destructive' },
  importante: { label: 'Importante', className: 'bg-orange-100 text-orange-800 hover:bg-orange-100' },
  aviso: { label: 'Aviso', variant: 'secondary' },
  info: { label: 'Info', variant: 'outline' },
}

const ESTADO_LABEL: Record<EstadoAlerta, string> = {
  ativo: 'Ativo',
  resolvido: 'Resolvido',
}

const CATEGORIA_LABELS: Record<string, string> = {
  tensao_zero: 'Tensao zero — usina desligada',
  sobretensao: 'Sobretensao — tensao AC >= 240V',
  corrente_baixa: 'Corrente baixa prolongada',
  sem_geracao_diurna: 'Sem geracao em horario comercial (8h-18h)',
  sem_comunicacao: 'Sem comunicacao — possivel falha de Wi-Fi',
  geracao_abaixo: 'Geracao abaixo do previsto',
  geracao_acima: 'Geracao acima do previsto',
  temperatura_alta: 'Temperatura elevada do inversor',
  outro: 'Outro',
}

function NivelBadge({ nivel }: { nivel: NivelAlerta }) {
  const config = NIVEL_CONFIG[nivel]
  if (config.className) {
    return <Badge className={config.className}>{config.label}</Badge>
  }
  return <Badge variant={config.variant}>{config.label}</Badge>
}

export function AlertaDetalhePage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { data, loading, error, refetch } = useAlerta(id ?? '')

  function handleVoltar() {
    void navigate('/alertas')
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-48" />
        <Card>
          <CardContent className="pt-6 space-y-4">
            <Skeleton className="h-6 w-full" />
            <Skeleton className="h-6 w-3/4" />
            <Skeleton className="h-6 w-1/2" />
          </CardContent>
        </Card>
      </div>
    )
  }

  if (error) {
    return (
      <div className="space-y-4">
        <Button variant="ghost" onClick={handleVoltar} className="gap-2">
          <ArrowLeftIcon className="size-4" />
          Voltar
        </Button>
        <div className="text-center py-12 text-destructive">
          {error}{' '}
          <button onClick={() => void refetch()} className="underline hover:no-underline">
            Tentar novamente
          </button>
        </div>
      </div>
    )
  }

  if (!data) {
    return (
      <div className="space-y-4">
        <Button variant="ghost" onClick={handleVoltar} className="gap-2">
          <ArrowLeftIcon className="size-4" />
          Voltar
        </Button>
        <p className="text-center py-12 text-muted-foreground">Alerta nao encontrado</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" onClick={handleVoltar} className="gap-2">
          <ArrowLeftIcon className="size-4" />
          Voltar
        </Button>
        <h1 className="text-2xl font-bold">Detalhe do Alerta</h1>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-start justify-between gap-4">
            <div className="space-y-1">
              <CardTitle className="text-lg leading-tight">{data.mensagem}</CardTitle>
              <div className="flex items-center gap-2">
                {data.origem === 'interno' ? (
                  <Badge className="bg-blue-100 text-blue-800 hover:bg-blue-100">Alerta Interno</Badge>
                ) : (
                  <Badge variant="outline">Alerta do Provedor</Badge>
                )}
                {data.categoria && (
                  <span className="text-xs text-muted-foreground">
                    {CATEGORIA_LABELS[data.categoria] || data.categoria}
                  </span>
                )}
              </div>
            </div>
            <NivelBadge nivel={data.nivel} />
          </div>
        </CardHeader>
        <CardContent>
          <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-4 text-sm">
            <div>
              <dt className="text-muted-foreground font-medium">Usina</dt>
              <dd className="mt-1">{data.usina_nome}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground font-medium">Estado Atual</dt>
              <dd className="mt-1">{ESTADO_LABEL[data.estado] || data.estado}</dd>
            </div>
            {data.equipamento_sn && (
              <div>
                <dt className="text-muted-foreground font-medium">Equipamento (SN)</dt>
                <dd className="mt-1 font-mono text-xs">{data.equipamento_sn}</dd>
              </div>
            )}
            {data.id_alerta_provedor && data.origem === 'provedor' && (
              <div>
                <dt className="text-muted-foreground font-medium">ID Provedor</dt>
                <dd className="mt-1 font-mono text-xs">{data.id_alerta_provedor}</dd>
              </div>
            )}
            <div>
              <dt className="text-muted-foreground font-medium">Inicio</dt>
              <dd className="mt-1">{new Date(data.inicio).toLocaleString('pt-BR')}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground font-medium">Fim</dt>
              <dd className="mt-1">
                {data.fim ? new Date(data.fim).toLocaleString('pt-BR') : '—'}
              </dd>
            </div>
            {data.sugestao && (
              <div className="sm:col-span-2">
                <dt className="text-muted-foreground font-medium">Sugestao / Diagnostico</dt>
                <dd className="mt-1">{data.sugestao}</dd>
              </div>
            )}
          </dl>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Atualizar Alerta</CardTitle>
        </CardHeader>
        <CardContent>
          <AlertaEstadoForm alerta={data} onSuccess={() => void refetch()} />
        </CardContent>
      </Card>
    </div>
  )
}
