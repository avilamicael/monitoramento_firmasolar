import { useState } from 'react'
import { toast } from 'sonner'
import { Loader2Icon, PauseCircleIcon, PlayCircleIcon } from 'lucide-react'

import api from '@/lib/api'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'

interface AtivoToggleButtonProps {
  usinaId: string
  ativo: boolean
  onChange: () => void
}

/**
 * Botão de alternância do campo `ativo` da usina.
 *
 * Quando desativada (ativo=false), a coleta para de processar snapshots e
 * alertas dessa usina. Ativa = retoma a coleta no próximo ciclo.
 */
export function AtivoToggleButton({ usinaId, ativo, onChange }: AtivoToggleButtonProps) {
  const [saving, setSaving] = useState(false)

  async function handleToggle() {
    const novoEstado = !ativo
    const confirmacao = window.confirm(
      novoEstado
        ? 'Reativar coleta desta usina? Ela voltará a ser processada no próximo ciclo.'
        : 'Desativar coleta desta usina? A coleta dos dados e a geração de alertas serão pausadas.',
    )
    if (!confirmacao) return

    setSaving(true)
    try {
      await api.patch(`/api/usinas/${usinaId}/`, { ativo: novoEstado })
      toast.success(novoEstado ? 'Coleta reativada.' : 'Coleta pausada.')
      onChange()
    } catch {
      toast.error('Erro ao atualizar estado da usina.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="flex items-center gap-2">
      <Badge variant={ativo ? 'default' : 'secondary'} className="text-xs">
        {ativo ? 'Coleta ativa' : 'Coleta pausada'}
      </Badge>
      <Button
        variant="outline"
        size="sm"
        onClick={handleToggle}
        disabled={saving}
        title={ativo ? 'Pausar coleta desta usina' : 'Retomar coleta desta usina'}
      >
        {saving ? (
          <Loader2Icon className="size-3.5 animate-spin" />
        ) : ativo ? (
          <>
            <PauseCircleIcon className="size-3.5 mr-1" />
            Pausar coleta
          </>
        ) : (
          <>
            <PlayCircleIcon className="size-3.5 mr-1" />
            Reativar coleta
          </>
        )}
      </Button>
    </div>
  )
}
