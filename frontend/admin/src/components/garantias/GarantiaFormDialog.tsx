import { useEffect, useMemo, useState } from 'react'
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
import type { GarantiaUsina } from '@/types/garantias'

interface GarantiaFormDialogProps {
  garantia: GarantiaUsina | null
  open: boolean
  onClose: () => void
  onSuccess: () => void
}

export function GarantiaFormDialog({
  garantia,
  open,
  onClose,
  onSuccess,
}: GarantiaFormDialogProps) {
  const [dataInicio, setDataInicio] = useState('')
  const [meses, setMeses] = useState('12')
  const [observacoes, setObservacoes] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

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
  }, [garantia])

  // Preview de data_fim calculado em tempo real (D-03)
  const dataFimPreview = useMemo(() => {
    if (!dataInicio || !meses || parseInt(meses) < 1) return null
    const d = new Date(dataInicio + 'T00:00:00') // T00:00:00 evita timezone shift
    d.setMonth(d.getMonth() + parseInt(meses))
    return d.toLocaleDateString('pt-BR')
  }, [dataInicio, meses])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)

    // Validacao local (T-05-07)
    if (!dataInicio) {
      setError('Data de inicio e obrigatoria')
      return
    }
    const mesesNum = parseInt(meses)
    if (isNaN(mesesNum) || mesesNum < 1) {
      setError('Duracao deve ser pelo menos 1 mes')
      return
    }

    setSaving(true)
    try {
      await api.put(`/api/usinas/${garantia!.usina_id}/garantia/`, {
        data_inicio: dataInicio,
        meses: mesesNum,
        observacoes,
      })
      toast.success('Garantia salva com sucesso')
      onSuccess()
    } catch {
      // Erro generico — nao expor detalhes do backend (T-05-09)
      toast.error('Erro ao salvar garantia')
      setError('Erro ao salvar')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={(isOpen) => { if (!isOpen) onClose() }}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Editar Garantia</DialogTitle>
          {garantia?.usina_nome && (
            <DialogDescription>{garantia.usina_nome}</DialogDescription>
          )}
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="data-inicio">Data de Inicio</Label>
            <Input
              id="data-inicio"
              type="date"
              value={dataInicio}
              onChange={(e) => setDataInicio(e.target.value)}
              required
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="meses">Duracao (meses)</Label>
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
            <Label htmlFor="observacoes">Observacoes</Label>
            <Input
              id="observacoes"
              value={observacoes}
              onChange={(e) => setObservacoes(e.target.value)}
              placeholder="Observacoes (opcional)"
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

          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose}>
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
