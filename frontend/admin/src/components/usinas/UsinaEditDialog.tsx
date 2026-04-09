import { useState, useEffect } from 'react'
import { toast } from 'sonner'
import api from '@/lib/api'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import type { UsinaResumo } from '@/types/usinas'

interface UsinaEditDialogProps {
  usina: UsinaResumo | null
  open: boolean
  onClose: () => void
  onSuccess: () => void
}

export function UsinaEditDialog({ usina, open, onClose, onSuccess }: UsinaEditDialogProps) {
  const [nome, setNome] = useState('')
  const [capacidadeKwp, setCapacidadeKwp] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (usina !== null) {
      setNome(usina.nome)
      setCapacidadeKwp(String(usina.capacidade_kwp))
      setError(null)
    }
  }, [usina])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()

    if (!nome.trim()) {
      setError('Nome e obrigatorio')
      return
    }

    const capacidade = parseFloat(capacidadeKwp)
    if (isNaN(capacidade) || capacidade <= 0) {
      setError('Capacidade deve ser um numero positivo')
      return
    }

    setSaving(true)
    setError(null)
    try {
      await api.patch(`/api/usinas/${usina!.id}/`, {
        nome: nome.trim(),
        capacidade_kwp: capacidade,
      })
      toast.success('Usina atualizada com sucesso')
      onSuccess()
    } catch {
      toast.error('Erro ao atualizar usina')
      setError('Erro ao salvar')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={(isOpen) => { if (!isOpen) onClose() }}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Editar Usina</DialogTitle>
          <DialogDescription>{usina?.nome}</DialogDescription>
        </DialogHeader>

        <form onSubmit={(e) => { void handleSubmit(e) }} className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="nome">Nome</Label>
            <Input
              id="nome"
              value={nome}
              onChange={(e) => setNome(e.target.value)}
              placeholder="Nome da usina"
              disabled={saving}
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="capacidade">Capacidade (kWp)</Label>
            <Input
              id="capacidade"
              type="number"
              step="0.01"
              min="0"
              value={capacidadeKwp}
              onChange={(e) => setCapacidadeKwp(e.target.value)}
              placeholder="Ex: 12.5"
              disabled={saving}
            />
          </div>

          {error && <p className="text-sm text-destructive">{error}</p>}

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
