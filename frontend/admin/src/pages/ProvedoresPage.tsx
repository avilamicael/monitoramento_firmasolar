import { useState } from 'react'
import { toast } from 'sonner'
import {
  AlertTriangleIcon,
  CheckCircle2Icon,
  Loader2Icon,
  PencilIcon,
  PlayIcon,
  PlusIcon,
  Trash2Icon,
  XCircleIcon,
} from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { ProvedorFormDialog } from '@/components/provedores/ProvedorFormDialog'
import { extrairErroProvedor, useProvedores } from '@/hooks/use-provedores'
import type { CredencialProvedor, CredencialWritePayload } from '@/types/provedores'

function formatarDataHora(iso: string): string {
  return new Date(iso).toLocaleString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function renderTokenStatus(cred: CredencialProvedor): React.ReactNode {
  if (!cred.usa_token_manual) return <span className="text-xs text-muted-foreground">—</span>
  const status = cred.token_status
  if (!status?.configurado) {
    return (
      <Badge variant="destructive" className="text-xs">Sem token</Badge>
    )
  }
  const dias = status.dias_restantes
  if (dias == null) {
    return <Badge variant="secondary" className="text-xs">Válido</Badge>
  }
  if (dias < 0) {
    return <Badge variant="destructive" className="text-xs">Expirado</Badge>
  }
  if (dias <= 7) {
    return (
      <Badge className="bg-red-100 text-red-800 text-xs">
        Expira em {dias}d
      </Badge>
    )
  }
  if (dias <= 14) {
    return (
      <Badge className="bg-amber-100 text-amber-800 text-xs">
        Expira em {dias}d
      </Badge>
    )
  }
  return (
    <Badge className="bg-green-100 text-green-800 text-xs">
      {dias}d restantes
    </Badge>
  )
}

function renderUltimaColeta(cred: CredencialProvedor): React.ReactNode {
  const u = cred.ultima_coleta
  if (!u) return <span className="text-xs text-muted-foreground">Nunca coletado</span>
  const cor =
    u.status === 'sucesso' ? 'text-green-600' :
    u.status === 'parcial' ? 'text-amber-600' : 'text-red-600'
  return (
    <div className="text-xs space-y-0.5">
      <div className={`font-medium ${cor}`}>{u.status}</div>
      <div className="text-muted-foreground">{formatarDataHora(u.iniciado_em)}</div>
      <div className="text-muted-foreground">{u.usinas_coletadas} usinas / {u.inversores_coletados} inv.</div>
    </div>
  )
}

export function ProvedoresPage() {
  const { data, meta, loading, error, criar, atualizar, remover, forcarColeta } = useProvedores()
  const [formTarget, setFormTarget] = useState<CredencialProvedor | null | 'novo'>(null)
  const [acaoEmAndamento, setAcaoEmAndamento] = useState<string | null>(null)

  async function handleSubmit(payload: CredencialWritePayload, id: string | null) {
    if (id) await atualizar(id, payload)
    else await criar(payload)
  }

  async function handleForcarColeta(cred: CredencialProvedor) {
    setAcaoEmAndamento(cred.id)
    try {
      await forcarColeta(cred.id)
      toast.success(`Coleta do ${cred.provedor_display} disparada.`)
    } catch (err) {
      toast.error(extrairErroProvedor(err, 'Erro ao disparar coleta.'))
    } finally {
      setAcaoEmAndamento(null)
    }
  }

  async function handleToggleAtivo(cred: CredencialProvedor) {
    setAcaoEmAndamento(cred.id)
    try {
      await atualizar(cred.id, { ativo: !cred.ativo })
      toast.success(`Provedor ${cred.ativo ? 'desativado' : 'ativado'}.`)
    } catch (err) {
      toast.error(extrairErroProvedor(err, 'Erro ao atualizar provedor.'))
    } finally {
      setAcaoEmAndamento(null)
    }
  }

  async function handleRemover(cred: CredencialProvedor) {
    const confirmacao = window.confirm(
      `Remover o provedor "${cred.provedor_display}"? Essa ação apaga a credencial e o cache de token. As usinas coletadas permanecem no banco.`,
    )
    if (!confirmacao) return
    setAcaoEmAndamento(cred.id)
    try {
      await remover(cred.id)
      toast.success('Provedor removido.')
    } catch (err) {
      toast.error(extrairErroProvedor(err, 'Erro ao remover provedor.'))
    } finally {
      setAcaoEmAndamento(null)
    }
  }

  if (error) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Provedores</CardTitle>
          <CardDescription className="text-destructive">{error}</CardDescription>
        </CardHeader>
      </Card>
    )
  }

  const ativosJaCadastrados = new Set(data?.map((d) => d.provedor) ?? [])
  const podeCriar = meta && meta.provedores.some((p) => !ativosJaCadastrados.has(p.valor))

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Gestão de Provedores</h1>
          <p className="text-sm text-muted-foreground">
            Credenciais, intervalos e coleta por API de cada provedor.
          </p>
        </div>
        <Button
          onClick={() => setFormTarget('novo')}
          disabled={!podeCriar}
          title={!podeCriar ? 'Todos os provedores já estão cadastrados' : ''}
        >
          <PlusIcon className="size-4 mr-1" />
          Novo provedor
        </Button>
      </div>

      {loading ? (
        <div className="space-y-2">
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-12 w-full" />
        </div>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Provedor</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Intervalo</TableHead>
              <TableHead>Token</TableHead>
              <TableHead>Última coleta</TableHead>
              <TableHead className="text-right">Ações</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {(data ?? []).length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center text-muted-foreground">
                  Nenhum provedor cadastrado
                </TableCell>
              </TableRow>
            ) : (
              (data ?? []).map((cred) => {
                const emAndamento = acaoEmAndamento === cred.id
                return (
                  <TableRow key={cred.id}>
                    <TableCell className="font-medium">{cred.provedor_display}</TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1.5">
                        {cred.ativo ? (
                          <Badge className="bg-green-100 text-green-800 gap-1 text-xs">
                            <CheckCircle2Icon className="size-3" />
                            Ativo
                          </Badge>
                        ) : (
                          <Badge variant="secondary" className="gap-1 text-xs">
                            <XCircleIcon className="size-3" />
                            Inativo
                          </Badge>
                        )}
                        {cred.precisa_atencao && (
                          <Badge variant="destructive" className="gap-1 text-xs">
                            <AlertTriangleIcon className="size-3" />
                            Atenção
                          </Badge>
                        )}
                      </div>
                    </TableCell>
                    <TableCell className="text-sm">{cred.intervalo_coleta_minutos} min</TableCell>
                    <TableCell>{renderTokenStatus(cred)}</TableCell>
                    <TableCell>{renderUltimaColeta(cred)}</TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-1">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleForcarColeta(cred)}
                          disabled={emAndamento || !cred.ativo}
                          title={!cred.ativo ? 'Ative o provedor primeiro' : 'Forçar coleta agora'}
                        >
                          {emAndamento ? <Loader2Icon className="size-3.5 animate-spin" /> : <PlayIcon className="size-3.5" />}
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleToggleAtivo(cred)}
                          disabled={emAndamento}
                        >
                          {cred.ativo ? 'Desativar' : 'Ativar'}
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => setFormTarget(cred)}
                          disabled={emAndamento}
                        >
                          <PencilIcon className="size-3.5" />
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleRemover(cred)}
                          disabled={emAndamento}
                        >
                          <Trash2Icon className="size-3.5 text-destructive" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                )
              })
            )}
          </TableBody>
        </Table>
      )}

      <ProvedorFormDialog
        credencial={formTarget && formTarget !== 'novo' ? formTarget : null}
        meta={meta}
        open={formTarget !== null}
        onClose={() => setFormTarget(null)}
        onSubmit={handleSubmit}
      />
    </div>
  )
}
