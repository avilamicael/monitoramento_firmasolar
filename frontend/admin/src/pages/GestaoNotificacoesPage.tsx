import { useEffect, useState } from 'react'
import { toast } from 'sonner'
import { MailIcon, MessageSquareIcon, WebhookIcon, Loader2Icon } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { Skeleton } from '@/components/ui/skeleton'
import { useNotificacoesConfig } from '@/hooks/use-notificacoes-config'
import type {
  CanalNotificacao,
  ConfiguracaoNotificacao,
  ConfiguracaoNotificacaoPayload,
} from '@/types/notificacoes-config'

interface CanalMeta {
  canal: CanalNotificacao
  titulo: string
  descricao: string
  icone: typeof MailIcon
  placeholder: string
  help: string
}

const CANAIS: CanalMeta[] = [
  {
    canal: 'email',
    titulo: 'E-mail',
    descricao: 'Envia notificações por e-mail para os endereços cadastrados.',
    icone: MailIcon,
    placeholder: 'suporte@firmasolar.com.br\nequipe@firmasolar.com.br',
    help: 'Um e-mail por linha (ou separados por vírgula).',
  },
  {
    canal: 'whatsapp',
    titulo: 'WhatsApp',
    descricao: 'Dispara mensagem de WhatsApp para os números cadastrados.',
    icone: MessageSquareIcon,
    placeholder: '+5548999999999\n+5511988888888',
    help: 'Formato internacional com DDI (ex: +5548999999999).',
  },
  {
    canal: 'webhook',
    titulo: 'Webhook',
    descricao: 'Envia POST JSON para URLs externas (integrar com CRM/ERP).',
    icone: WebhookIcon,
    placeholder: 'https://crm.empresa.com/webhook/firmasolar\nhttps://n8n.example.com/webhook/abc',
    help: 'Uma URL por linha. O payload inclui dados do alerta (mensagem, nível, usina).',
  },
]

function CanalCard({
  meta, config, onSalvar, salvando,
}: {
  meta: CanalMeta
  config: ConfiguracaoNotificacao | null
  onSalvar: (payload: ConfiguracaoNotificacaoPayload) => Promise<void>
  salvando: boolean
}) {
  const Icone = meta.icone
  const [ativo, setAtivo] = useState(config?.ativo ?? false)
  const [destinatarios, setDestinatarios] = useState(config?.destinatarios ?? '')
  const [notificarCritico, setNotificarCritico] = useState(config?.notificar_critico ?? true)
  const [notificarImportante, setNotificarImportante] = useState(config?.notificar_importante ?? true)
  const [notificarAviso, setNotificarAviso] = useState(config?.notificar_aviso ?? false)
  const [notificarInfo, setNotificarInfo] = useState(config?.notificar_info ?? false)

  useEffect(() => {
    setAtivo(config?.ativo ?? false)
    setDestinatarios(config?.destinatarios ?? '')
    setNotificarCritico(config?.notificar_critico ?? true)
    setNotificarImportante(config?.notificar_importante ?? true)
    setNotificarAviso(config?.notificar_aviso ?? false)
    setNotificarInfo(config?.notificar_info ?? false)
  }, [config])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    await onSalvar({
      ativo,
      destinatarios,
      notificar_critico: notificarCritico,
      notificar_importante: notificarImportante,
      notificar_aviso: notificarAviso,
      notificar_info: notificarInfo,
    })
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-start gap-3">
          <Icone className="size-5 mt-0.5 text-muted-foreground" />
          <div className="flex-1">
            <CardTitle className="text-base flex items-center gap-2">
              {meta.titulo}
              <span className={`text-xs rounded-full px-2 py-0.5 ${ativo ? 'bg-green-100 text-green-800' : 'bg-muted text-muted-foreground'}`}>
                {ativo ? 'Ativo' : 'Inativo'}
              </span>
            </CardTitle>
            <CardDescription className="mt-1">{meta.descricao}</CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="flex items-center gap-2">
            <input
              id={`ativo-${meta.canal}`}
              type="checkbox"
              checked={ativo}
              onChange={(e) => setAtivo(e.target.checked)}
              className="size-4"
            />
            <Label htmlFor={`ativo-${meta.canal}`} className="font-normal cursor-pointer">
              Canal ativo (desmarque para desligar este canal sem perder as configurações)
            </Label>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor={`dest-${meta.canal}`}>Destinatários</Label>
            <textarea
              id={`dest-${meta.canal}`}
              rows={4}
              value={destinatarios}
              onChange={(e) => setDestinatarios(e.target.value)}
              placeholder={meta.placeholder}
              className="w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring font-mono"
            />
            <p className="text-xs text-muted-foreground">{meta.help}</p>
          </div>

          <div className="space-y-2">
            <Label>Notificar alertas de nível:</Label>
            <div className="grid grid-cols-2 gap-2">
              <label className="flex items-center gap-2 text-sm font-normal cursor-pointer">
                <input
                  type="checkbox"
                  checked={notificarCritico}
                  onChange={(e) => setNotificarCritico(e.target.checked)}
                  className="size-4"
                />
                <span className="text-red-700">Crítico</span>
              </label>
              <label className="flex items-center gap-2 text-sm font-normal cursor-pointer">
                <input
                  type="checkbox"
                  checked={notificarImportante}
                  onChange={(e) => setNotificarImportante(e.target.checked)}
                  className="size-4"
                />
                <span className="text-orange-700">Importante</span>
              </label>
              <label className="flex items-center gap-2 text-sm font-normal cursor-pointer">
                <input
                  type="checkbox"
                  checked={notificarAviso}
                  onChange={(e) => setNotificarAviso(e.target.checked)}
                  className="size-4"
                />
                <span className="text-amber-700">Aviso</span>
              </label>
              <label className="flex items-center gap-2 text-sm font-normal cursor-pointer">
                <input
                  type="checkbox"
                  checked={notificarInfo}
                  onChange={(e) => setNotificarInfo(e.target.checked)}
                  className="size-4"
                />
                <span className="text-blue-700">Info</span>
              </label>
            </div>
          </div>

          <div className="flex justify-end">
            <Button type="submit" disabled={salvando}>
              {salvando ? <Loader2Icon className="size-4 animate-spin mr-1" /> : null}
              Salvar
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  )
}

export function GestaoNotificacoesPage() {
  const { data, loading, error, criar, atualizar, extrairErro } = useNotificacoesConfig()
  const [salvandoCanal, setSalvandoCanal] = useState<CanalNotificacao | null>(null)

  const porCanal: Record<CanalNotificacao, ConfiguracaoNotificacao | null> = {
    email: data?.find((c) => c.canal === 'email') ?? null,
    whatsapp: data?.find((c) => c.canal === 'whatsapp') ?? null,
    webhook: data?.find((c) => c.canal === 'webhook') ?? null,
  }

  async function handleSalvar(canal: CanalNotificacao, payload: ConfiguracaoNotificacaoPayload) {
    setSalvandoCanal(canal)
    try {
      const existente = porCanal[canal]
      if (existente) {
        await atualizar(existente.id, payload)
      } else {
        await criar(canal, payload)
      }
      toast.success(`Canal "${canal}" salvo.`)
    } catch (err) {
      toast.error(extrairErro(err, 'Erro ao salvar canal.'))
    } finally {
      setSalvandoCanal(null)
    }
  }

  if (error) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Gestão de Notificações</CardTitle>
          <CardDescription className="text-destructive">{error}</CardDescription>
        </CardHeader>
      </Card>
    )
  }

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold">Gestão de Notificações</h1>
        <p className="text-sm text-muted-foreground">
          Configure quem recebe as notificações de alertas, por quais canais e para quais níveis de severidade.
          A configuração é global — todos os destinatários cadastrados recebem.
        </p>
      </div>

      {loading ? (
        <div className="space-y-3">
          {[0, 1, 2].map((i) => <Skeleton key={i} className="h-60 w-full" />)}
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4">
          {CANAIS.map((meta) => (
            <CanalCard
              key={meta.canal}
              meta={meta}
              config={porCanal[meta.canal]}
              onSalvar={(p) => handleSalvar(meta.canal, p)}
              salvando={salvandoCanal === meta.canal}
            />
          ))}
        </div>
      )}
    </div>
  )
}
