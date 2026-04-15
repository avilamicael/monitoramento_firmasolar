import { useEffect, useState } from 'react'
import { toast } from 'sonner'

import api from '@/lib/api'
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

interface ConfigAlertasDialogProps {
  open: boolean
  usinaId: string
  usinaNome: string
  valorAtual: number
  onClose: () => void
  onSuccess: () => void
}

export function ConfigAlertasDialog({
  open, usinaId, usinaNome, valorAtual, onClose, onSuccess,
}: ConfigAlertasDialogProps) {
  const [valor, setValor] = useState(String(valorAtual))
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (open) setValor(String(valorAtual))
  }, [open, valorAtual])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const num = Number(valor)
    if (!Number.isFinite(num) || num < 180 || num > 280) {
      toast.error('Informe um valor entre 180V e 280V.')
      return
    }
    setSaving(true)
    try {
      await api.patch(`/api/usinas/${usinaId}/`, { tensao_sobretensao_v: num })
      toast.success('Limite de sobretensão atualizado.')
      onSuccess()
      onClose()
    } catch {
      toast.error('Erro ao salvar.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={(v) => { if (!v) onClose() }}>
      <DialogContent className="sm:max-w-sm">
        <DialogHeader>
          <DialogTitle>Configurar alertas</DialogTitle>
          <DialogDescription>{usinaNome}</DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="tensao">Limite de sobretensão AC (V)</Label>
            <Input
              id="tensao"
              type="number"
              min={180}
              max={280}
              step={1}
              value={valor}
              onChange={(e) => setValor(e.target.value)}
              required
            />
            <p className="text-xs text-muted-foreground">
              Gera alerta interno quando a tensão AC de qualquer inversor desta usina
              atinge ou ultrapassa este valor. Ajuste conforme a realidade da rede elétrica
              local (padrão 240V).
            </p>
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose} disabled={saving}>
              Cancelar
            </Button>
            <Button type="submit" disabled={saving}>
              {saving ? 'Salvando...' : 'Salvar'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
