import { useState, useEffect } from 'react'
import { toast } from 'sonner'
import { Loader2Icon } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import api from '@/lib/api'
import type { AlertaDetalhe, EstadoAlerta } from '@/types/alertas'

interface AlertaEstadoFormProps {
  alerta: AlertaDetalhe
  onSuccess: () => void
}

const ESTADO_OPCOES: { value: EstadoAlerta; label: string }[] = [
  { value: 'ativo', label: 'Ativo' },
  { value: 'resolvido', label: 'Resolvido' },
]

export function AlertaEstadoForm({ alerta, onSuccess }: AlertaEstadoFormProps) {
  const [estado, setEstado] = useState<EstadoAlerta>(alerta.estado)
  const [anotacoes, setAnotacoes] = useState<string>(alerta.anotacoes ?? '')
  const [isSubmitting, setIsSubmitting] = useState(false)

  // Sincronizar state quando o alerta mudar (ex: refetch apos PATCH)
  useEffect(() => {
    setEstado(alerta.estado)
    setAnotacoes(alerta.anotacoes ?? '')
  }, [alerta.id])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setIsSubmitting(true)
    try {
      await api.patch(`/api/alertas/${alerta.id}/`, { estado, anotacoes })
      toast.success('Alerta atualizado com sucesso')
      onSuccess()
    } catch {
      toast.error('Erro ao atualizar alerta')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <form onSubmit={(e) => void handleSubmit(e)} className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="estado">Estado</Label>
        <Select
          value={estado}
          onValueChange={(value) => setEstado(value as EstadoAlerta)}
        >
          <SelectTrigger id="estado" className="w-full">
            <SelectValue placeholder="Selecione o estado" />
          </SelectTrigger>
          <SelectContent>
            {ESTADO_OPCOES.map((opcao) => (
              <SelectItem key={opcao.value} value={opcao.value}>
                {opcao.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-2">
        <Label htmlFor="anotacoes">Anotações</Label>
        <textarea
          id="anotacoes"
          value={anotacoes}
          onChange={(e) => setAnotacoes(e.target.value)}
          className="w-full min-h-[100px] rounded-md border border-input bg-background px-3 py-2 text-sm resize-y focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
          placeholder="Adicione anotações sobre o atendimento..."
        />
      </div>

      <Button type="submit" disabled={isSubmitting}>
        {isSubmitting && <Loader2Icon className="mr-2 size-4 animate-spin" />}
        Salvar
      </Button>
    </form>
  )
}
