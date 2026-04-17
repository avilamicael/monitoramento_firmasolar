import { useEffect, useMemo, useState } from 'react'
import { toast } from 'sonner'
import { Trash2Icon } from 'lucide-react'
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
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import type { GarantiaUsina } from '@/types/garantias'

interface GarantiaFormDialogProps {
  garantia: GarantiaUsina | null
  usinaId: string | null
  usinaNome: string | null
  open: boolean
  onClose: () => void
  onSuccess: () => void
}

export function GarantiaFormDialog({
  garantia,
  usinaId,
  usinaNome,
  open,
  onClose,
  onSuccess,
}: GarantiaFormDialogProps) {
  const [dataInicio, setDataInicio] = useState('')
  const [meses, setMeses] = useState('12')
  const [observacoes, setObservacoes] = useState('')
  const [saving, setSaving] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const isEditing = garantia !== null
  const targetUsinaId = garantia?.usina_id ?? usinaId
  const targetUsinaNome = garantia?.usina_nome ?? usinaNome

  useEffect(() => {
    if (garantia !== null) {
      setDataInicio(garantia.data_inicio)
      setMeses(String(garantia.meses))
      setObservacoes(garantia.observacoes)
    } else {
      setDataInicio('')
      setMeses('12')
      setObservacoes('')
    }
    setError(null)
  }, [garantia, usinaId])

  const dataFimPreview = useMemo(() => {
    if (!dataInicio || !meses || parseInt(meses) < 1) return null
    const d = new Date(dataInicio + 'T00:00:00')
    d.setMonth(d.getMonth() + parseInt(meses))
    return d.toLocaleDateString('pt-BR')
  }, [dataInicio, meses])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)

    if (!dataInicio) {
      setError('Data de início é obrigatória')
      return
    }
    const mesesNum = parseInt(meses)
    if (isNaN(mesesNum) || mesesNum < 1) {
      setError('Duração deve ser pelo menos 1 mês')
      return
    }
    if (!targetUsinaId) {
      setError('Usina não identificada')
      return
    }

    setSaving(true)
    try {
      await api.put(`/api/usinas/${targetUsinaId}/garantia/`, {
        data_inicio: dataInicio,
        meses: mesesNum,
        observacoes,
      })
      toast.success(isEditing ? 'Garantia atualizada' : 'Garantia criada')
      onSuccess()
    } catch {
      toast.error('Erro ao salvar garantia')
      setError('Erro ao salvar')
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete() {
    if (!targetUsinaId) {
      toast.error('Usina não identificada')
      return
    }

    setDeleting(true)
    try {
      await api.delete(`/api/usinas/${targetUsinaId}/garantia/`)
      toast.success('Garantia removida com sucesso')
      setShowDeleteConfirm(false)
      onSuccess()
    } catch {
      toast.error('Erro ao remover garantia')
    } finally {
      setDeleting(false)
    }
  }

  return (
    <>
      <Dialog open={open} onOpenChange={(isOpen) => { if (!isOpen) onClose() }}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>{isEditing ? 'Editar Garantia' : 'Adicionar Garantia'}</DialogTitle>
            {targetUsinaNome && (
              <DialogDescription>{targetUsinaNome}</DialogDescription>
            )}
          </DialogHeader>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="data-inicio">Data de Início</Label>
              <Input
                id="data-inicio"
                type="date"
                value={dataInicio}
                onChange={(e) => setDataInicio(e.target.value)}
                required
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="meses">Duração (meses)</Label>
              <Input
                id="meses"
                type="number"
                min="1"
                step="1"
                value={meses}
                onChange={(e) => setMeses(e.target.value)}
                required
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="observacoes">Observações</Label>
              <Input
                id="observacoes"
                value={observacoes}
                onChange={(e) => setObservacoes(e.target.value)}
                placeholder="Observações (opcional)"
              />
            </div>

            {dataFimPreview && (
              <p className="text-sm text-muted-foreground">
                Data fim prevista:{' '}
                <span className="font-medium">{dataFimPreview}</span>
              </p>
            )}

            {error && (
              <p className="text-sm text-destructive">{error}</p>
            )}

            <DialogFooter className="flex justify-between">
              <div className="flex gap-2">
                {isEditing && (
                  <Button
                    type="button"
                    variant="destructive"
                    size="sm"
                    onClick={() => setShowDeleteConfirm(true)}
                  >
                    <Trash2Icon className="size-4 mr-1" />
                    Remover Garantia
                  </Button>
                )}
              </div>
              <div className="flex gap-2">
                <Button type="button" variant="outline" onClick={onClose}>
                  Cancelar
                </Button>
                <Button type="submit" disabled={saving}>
                  {saving ? 'Salvando...' : isEditing ? 'Atualizar' : 'Criar'}
                </Button>
              </div>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <AlertDialog open={showDeleteConfirm} onOpenChange={setShowDeleteConfirm}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Remover Garantia</AlertDialogTitle>
            <AlertDialogDescription>
              Tem certeza que deseja remover a garantia da usina {targetUsinaNome}?
              Esta ação não pode ser desfeita.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={deleting}>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              onClick={(e: React.MouseEvent) => {
                e.preventDefault()
                void handleDelete()
              }}
              disabled={deleting}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {deleting ? 'Removendo...' : 'Remover'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  )
}
