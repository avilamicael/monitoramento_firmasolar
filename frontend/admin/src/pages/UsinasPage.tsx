import { useState } from 'react'
import { Loader2Icon } from 'lucide-react'
import { useUsinas } from '@/hooks/use-usinas'
import { UsinasTable } from '@/components/usinas/UsinasTable'
import { UsinaEditDialog } from '@/components/usinas/UsinaEditDialog'
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
  PaginationPrevious,
  PaginationNext,
} from '@/components/ui/pagination'
import type { UsinaResumo, StatusGarantia } from '@/types/usinas'

export function UsinasPage() {
  const [provedor, setProvedor] = useState('')
  const [statusGarantia, setStatusGarantia] = useState('')
  const [page, setPage] = useState(1)
  const [editingUsina, setEditingUsina] = useState<UsinaResumo | null>(null)

  const { data, loading, error, refetch } = useUsinas({
    provedor: provedor || undefined,
    status_garantia: (statusGarantia as StatusGarantia) || undefined,
    page,
  })

  const totalPages = Math.ceil((data?.count ?? 0) / 20)

  function handleProvedorChange(value: string) {
    setProvedor(value === 'all' ? '' : value)
    setPage(1)
  }

  function handleStatusGarantiaChange(value: string) {
    setStatusGarantia(value === 'all' ? '' : value)
    setPage(1)
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <Select value={provedor} onValueChange={handleProvedorChange}>
          <SelectTrigger className="w-40">
            <SelectValue placeholder="Provedor" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todos</SelectItem>
            <SelectItem value="solis">Solis</SelectItem>
            <SelectItem value="growatt">Growatt</SelectItem>
          </SelectContent>
        </Select>

        <Select value={statusGarantia} onValueChange={handleStatusGarantiaChange}>
          <SelectTrigger className="w-48">
            <SelectValue placeholder="Status Garantia" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todos</SelectItem>
            <SelectItem value="ativa">Ativa</SelectItem>
            <SelectItem value="vencida">Vencida</SelectItem>
            <SelectItem value="sem_garantia">Sem Garantia</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {loading ? (
        <div className="flex justify-center py-8">
          <Loader2Icon className="size-6 animate-spin text-muted-foreground" />
        </div>
      ) : error ? (
        <div className="py-8 text-center text-destructive">{error}</div>
      ) : (
        <UsinasTable usinas={data?.results ?? []} onEdit={setEditingUsina} />
      )}

      {!loading && !error && (data?.count ?? 0) > 0 && (
        <Pagination>
          <PaginationContent>
            <PaginationItem>
              <PaginationPrevious
                text="Anterior"
                aria-disabled={!data?.previous}
                className={!data?.previous ? 'pointer-events-none opacity-50' : ''}
                onClick={(e) => {
                  e.preventDefault()
                  if (data?.previous) setPage((p) => p - 1)
                }}
                href="#"
              />
            </PaginationItem>
            <PaginationItem>
              <span className="px-4 text-sm text-muted-foreground">
                Pagina {page} de {totalPages}
              </span>
            </PaginationItem>
            <PaginationItem>
              <PaginationNext
                text="Proxima"
                aria-disabled={!data?.next}
                className={!data?.next ? 'pointer-events-none opacity-50' : ''}
                onClick={(e) => {
                  e.preventDefault()
                  if (data?.next) setPage((p) => p + 1)
                }}
                href="#"
              />
            </PaginationItem>
          </PaginationContent>
        </Pagination>
      )}

      <UsinaEditDialog
        usina={editingUsina}
        open={!!editingUsina}
        onClose={() => setEditingUsina(null)}
        onSuccess={() => {
          setEditingUsina(null)
          void refetch()
        }}
      />
    </div>
  )
}
