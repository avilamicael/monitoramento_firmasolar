import { useEffect, useState } from 'react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { extrairErroProvedor } from '@/hooks/use-provedores'
import type {
  CampoProvedor,
  CredencialProvedor,
  CredencialWritePayload,
  ProvedoresMetaResponse,
} from '@/types/provedores'

interface ProvedorFormDialogProps {
  credencial: CredencialProvedor | null
  meta: ProvedoresMetaResponse | null
  open: boolean
  onClose: () => void
  onSubmit: (payload: CredencialWritePayload, id: string | null) => Promise<void>
}

const INSTRUCOES_TOKEN_SOLARMAN = (
  <div className="rounded-md bg-blue-50 dark:bg-blue-950 border border-blue-200 dark:border-blue-900 p-3 text-xs space-y-1 leading-relaxed">
    <p className="font-semibold">Como obter o Token JWT do Solarman:</p>
    <ol className="list-decimal list-inside space-y-0.5">
      <li>
        Acesse{' '}
        <a
          href="https://globalpro.solarmanpv.com"
          target="_blank"
          rel="noopener noreferrer"
          className="text-primary underline"
        >
          globalpro.solarmanpv.com
        </a>{' '}
        e faça login.
      </li>
      <li>Pressione <b>F12</b> para abrir o DevTools.</li>
      <li>Aba <b>Application</b> → <b>Cookies</b> → <b>globalpro.solarmanpv.com</b>.</li>
      <li>
        Copie o valor completo do cookie <b>tokenKey</b> (começa com <code>eyJ...</code>).
      </li>
      <li>Cole no campo "Token JWT" e salve.</li>
    </ol>
    <p className="pt-1">
      <b>Válido por ~60 dias.</b> O sistema avisa quando estiver próximo de expirar.
    </p>
  </div>
)

export function ProvedorFormDialog({
  credencial,
  meta,
  open,
  onClose,
  onSubmit,
}: ProvedorFormDialogProps) {
  const isEditing = credencial !== null

  const [provedor, setProvedor] = useState<string>('')
  const [ativo, setAtivo] = useState(true)
  const [intervalo, setIntervalo] = useState<string>('30')
  const [credenciais, setCredenciais] = useState<Record<string, string>>({})
  const [tokenJwt, setTokenJwt] = useState('')
  const [saving, setSaving] = useState(false)

  const metaSelecionado = meta?.provedores.find((p) => p.valor === provedor) ?? null
  const camposRenderizar: CampoProvedor[] = metaSelecionado?.campos ?? []
  const usaTokenManual = metaSelecionado?.usa_token_manual ?? false

  // Provedores ainda não cadastrados — só aparecem no select quando criando nova credencial.
  const idsExistentes = new Set<string>()
  const provedoresDisponiveis = meta?.provedores.filter((p) => !idsExistentes.has(p.valor)) ?? []

  useEffect(() => {
    if (!open) return
    if (credencial) {
      setProvedor(credencial.provedor)
      setAtivo(credencial.ativo)
      setIntervalo(String(credencial.intervalo_coleta_minutos))
      setCredenciais({})
      setTokenJwt('')
    } else {
      setProvedor('')
      setAtivo(true)
      setIntervalo(String(meta?.intervalo_minimo_minutos ?? 30))
      setCredenciais({})
      setTokenJwt('')
    }
  }, [credencial, open, meta])

  function handleChangeCredencial(chave: string, valor: string) {
    setCredenciais((prev) => ({ ...prev, [chave]: valor }))
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()

    const intervaloNum = Number(intervalo)
    if (!Number.isInteger(intervaloNum) || intervaloNum < (meta?.intervalo_minimo_minutos ?? 30)) {
      toast.error(`Intervalo mínimo é ${meta?.intervalo_minimo_minutos ?? 30} minutos.`)
      return
    }

    const payload: CredencialWritePayload = {
      ativo,
      intervalo_coleta_minutos: intervaloNum,
    }

    if (!isEditing) {
      if (!provedor) {
        toast.error('Selecione o provedor.')
        return
      }
      payload.provedor = provedor

      // Em criação, todos os campos de credenciais são obrigatórios
      const creds: Record<string, string> = {}
      for (const campo of camposRenderizar) {
        const valor = (credenciais[campo.chave] ?? '').trim()
        if (!valor) {
          toast.error(`Preencha o campo "${campo.label}".`)
          return
        }
        creds[campo.chave] = valor
      }
      payload.credenciais = creds
    } else {
      // Em edição, só envia credenciais se o usuário preencheu ao menos um campo
      const preenchidos = camposRenderizar.filter((c) => (credenciais[c.chave] ?? '').trim())
      if (preenchidos.length > 0) {
        if (preenchidos.length !== camposRenderizar.length) {
          toast.error('Para atualizar credenciais, preencha todos os campos.')
          return
        }
        payload.credenciais = Object.fromEntries(
          camposRenderizar.map((c) => [c.chave, (credenciais[c.chave] ?? '').trim()]),
        )
      }
    }

    if (usaTokenManual && tokenJwt.trim()) {
      payload.token_jwt = tokenJwt.trim()
    }

    setSaving(true)
    try {
      await onSubmit(payload, credencial?.id ?? null)
      toast.success(isEditing ? 'Provedor atualizado.' : 'Provedor criado.')
      onClose()
    } catch (err) {
      toast.error(extrairErroProvedor(err, 'Erro ao salvar provedor.'))
    } finally {
      setSaving(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={(v) => { if (!v) onClose() }}>
      <DialogContent className="sm:max-w-lg max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{isEditing ? `Editar — ${credencial?.provedor_display}` : 'Novo Provedor'}</DialogTitle>
          <DialogDescription>
            {isEditing
              ? 'Deixe os campos de credenciais em branco para manter os atuais.'
              : 'Informe o provedor e as credenciais de acesso à API.'}
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="provedor">Provedor</Label>
            {isEditing ? (
              <Input id="provedor" value={credencial?.provedor_display} disabled />
            ) : (
              <Select value={provedor} onValueChange={setProvedor}>
                <SelectTrigger id="provedor">
                  <SelectValue placeholder="Selecione o provedor" />
                </SelectTrigger>
                <SelectContent>
                  {provedoresDisponiveis.map((p) => (
                    <SelectItem key={p.valor} value={p.valor}>
                      {p.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          </div>

          <div className="flex items-center gap-2">
            <input
              id="ativo"
              type="checkbox"
              checked={ativo}
              onChange={(e) => setAtivo(e.target.checked)}
              className="size-4"
            />
            <Label htmlFor="ativo" className="font-normal cursor-pointer">
              Coleta ativa
            </Label>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="intervalo">Intervalo de coleta (minutos)</Label>
            <Input
              id="intervalo"
              type="number"
              min={meta?.intervalo_minimo_minutos ?? 30}
              value={intervalo}
              onChange={(e) => setIntervalo(e.target.value)}
            />
            <p className="text-xs text-muted-foreground">
              Mínimo: {meta?.intervalo_minimo_minutos ?? 30} minutos.
            </p>
          </div>

          {provedor && camposRenderizar.length > 0 && (
            <div className="space-y-3 rounded-md border p-3">
              <p className="text-sm font-medium">Credenciais</p>
              {isEditing && credencial?.credenciais_preview && (
                <div className="text-xs text-muted-foreground space-y-0.5">
                  <p className="font-medium">Valores atuais (mascarados):</p>
                  {Object.entries(credencial.credenciais_preview).map(([chave, valor]) => (
                    <p key={chave}><b>{chave}</b>: {valor}</p>
                  ))}
                </div>
              )}
              {camposRenderizar.map((campo) => (
                <div key={campo.chave} className="space-y-1.5">
                  <Label htmlFor={`cred-${campo.chave}`}>{campo.label}</Label>
                  <Input
                    id={`cred-${campo.chave}`}
                    type={campo.tipo === 'senha' ? 'password' : 'text'}
                    autoComplete="off"
                    value={credenciais[campo.chave] ?? ''}
                    onChange={(e) => handleChangeCredencial(campo.chave, e.target.value)}
                    placeholder={isEditing ? 'Deixe em branco para manter' : ''}
                  />
                </div>
              ))}
            </div>
          )}

          {usaTokenManual && (
            <div className="space-y-2 rounded-md border p-3">
              <Label htmlFor="token_jwt">Token JWT</Label>
              <textarea
                id="token_jwt"
                rows={4}
                value={tokenJwt}
                onChange={(e) => setTokenJwt(e.target.value)}
                placeholder="eyJhbGciOiJSUzI1NiIs..."
                className="w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm font-mono break-all shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              />
              {INSTRUCOES_TOKEN_SOLARMAN}
            </div>
          )}

          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose} disabled={saving}>
              Cancelar
            </Button>
            <Button type="submit" disabled={saving || (!isEditing && !provedor)}>
              {saving ? 'Salvando...' : isEditing ? 'Atualizar' : 'Criar'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
