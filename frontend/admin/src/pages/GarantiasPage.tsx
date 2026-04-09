import { useState } from 'react'
import { useGarantias } from '@/hooks/use-garantias'
import { GarantiasTable } from '@/components/garantias/GarantiasTable'
import { GarantiaFormDialog } from '@/components/garantias/GarantiaFormDialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Pagination,
  PaginationContent,
  PaginationItem,
  PaginationNext,
  PaginationPrevious,
} from '@/components/ui/pagination'
import type { GarantiaUsina } from '@/types/garantias'

const PAGE_SIZE = 20

export function GarantiasPage() {
  const [filtro, setFiltro] = useState('')
  const [page, setPage] = useState(1)
  const [editingGarantia, setEditingGarantia] = useState<GarantiaUsina | null>(null)

  const { data, loading, error, refetch } = useGarantias({
    filtro: (filtro as 'ativas' | 'vencendo' | 'vencidas') || undefined,
    page,
  })

  function handleFiltroChange(value: string) {
    setFiltro(value === 'all' ? '' : value)
    setPage(1)
  }

  const totalPages = Math.ceil((data?.count ?? 0) / PAGE_SIZE)

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Garantias</h1>
      </div>

      <div className="flex items-center gap-3">
        <span className="text-sm text-muted-foreground">Filtrar por:</span>
        <Select value={filtro} onValueChange={handleFiltroChange}>
          <SelectTrigger className="w-48">
            <SelectValue placeholder="Todas" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todas</SelectItem>
            <SelectItem value="ativas">Ativas</SelectItem>
            <SelectItem value="vencendo">Vencendo em 30 dias</SelectItem>
            <SelectItem value="vencidas">Vencidas</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {loading && (
        <div className="flex justify-center py-12">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
        </div>
      )}

      {error && !loading && (
        <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">
          {error}
        </div>
      )}

      {!loading && !error && (
        <GarantiasTable
          garantias={data?.results ?? []}
          onEdit={setEditingGarantia}
        />
      )}

      {!loading && !error && totalPages > 1 && (
        <div className="flex items-center justify-between">
          <span className="text-sm text-muted-foreground">
            Pagina {page} de {totalPages}
          </span>
          <Pagination>
            <PaginationContent>
              <PaginationItem>
                <PaginationPrevious
                  text="Anterior"
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  aria-disabled={!data?.previous}
                  className={!data?.previous ? 'pointer-events-none opacity-50' : ''}
                />
              </PaginationItem>
              <PaginationItem>
                <PaginationNext
                  text="Proxima"
                  onClick={() => setPage((p) => p + 1)}
                  aria-disabled={!data?.next}
                  className={!data?.next ? 'pointer-events-none opacity-50' : ''}
                />
              </PaginationItem>
            </PaginationContent>
          </Pagination>
        </div>
      )}

      <GarantiaFormDialog
        garantia={editingGarantia}
        open={!!editingGarantia}
        onClose={() => setEditingGarantia(null)}
        onSuccess={() => {
          setEditingGarantia(null)
          refetch()
        }}
      />
    </div>
  )
}
