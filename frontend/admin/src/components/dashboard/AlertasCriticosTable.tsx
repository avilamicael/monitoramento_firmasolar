import { useState } from 'react'
import { ChevronDownIcon, ChevronRightIcon } from 'lucide-react'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Skeleton } from '@/components/ui/skeleton'
import type { AlertaResumo } from '@/types/alertas'

interface AlertasCriticosTableProps {
  alertas: AlertaResumo[]
  loading: boolean
  error: string | null
  onRetry: () => void
}

function formatarData(iso: string): string {
  const date = new Date(iso)
  return date.toLocaleDateString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function AlertasCriticosTable({ alertas, loading, error, onRetry }: AlertasCriticosTableProps) {
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set())

  function toggleExpand(id: string) {
    setExpandedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) {
        next.delete(id)
      } else {
        next.add(id)
      }
      return next
    })
  }

  if (error) {
    return (
      <p className="text-sm text-destructive">
        {error}{' '}
        <button onClick={onRetry} className="underline hover:no-underline">
          Tentar novamente
        </button>
      </p>
    )
  }

  if (loading) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} className="h-10 w-full" />
        ))}
      </div>
    )
  }

  if (alertas.length === 0) {
    return (
      <p className="text-muted-foreground text-center py-8">
        Nenhum alerta critico ativo
      </p>
    )
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead className="w-8" />
          <TableHead>Cliente</TableHead>
          <TableHead>Problema</TableHead>
          <TableHead>Data do Alarme</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {alertas.map((alerta) => {
          const isExpanded = expandedIds.has(alerta.id)
          return (
            <TableRow
              key={alerta.id}
              className="cursor-pointer"
              onClick={() => toggleExpand(alerta.id)}
              aria-expanded={isExpanded}
            >
              <TableCell colSpan={4} className="p-0">
                <div className="flex items-center gap-2 p-2">
                  {isExpanded ? (
                    <ChevronDownIcon className="size-4 shrink-0 text-muted-foreground" />
                  ) : (
                    <ChevronRightIcon className="size-4 shrink-0 text-muted-foreground" />
                  )}
                  <span className="flex-1 font-medium">{alerta.usina_nome}</span>
                  <span className="flex-1 text-muted-foreground">{alerta.mensagem}</span>
                  <span className="text-sm text-muted-foreground whitespace-nowrap">
                    {formatarData(alerta.inicio)}
                  </span>
                </div>
                {isExpanded && (
                  <div className="bg-muted/30 px-8 py-3 border-t space-y-1 text-sm">
                    <p>
                      <span className="font-medium">Usina:</span> {alerta.usina_nome}
                    </p>
                    <p>
                      <span className="font-medium">Problema:</span> {alerta.mensagem}
                    </p>
                    <p>
                      <span className="font-medium">Estado:</span> {alerta.estado}
                    </p>
                    <p>
                      <span className="font-medium">Nivel:</span> {alerta.nivel}
                    </p>
                    <p>
                      <span className="font-medium">Inicio:</span> {formatarData(alerta.inicio)}
                    </p>
                    {alerta.fim && (
                      <p>
                        <span className="font-medium">Fim:</span> {formatarData(alerta.fim)}
                      </p>
                    )}
                  </div>
                )}
              </TableCell>
            </TableRow>
          )
        })}
      </TableBody>
    </Table>
  )
}
