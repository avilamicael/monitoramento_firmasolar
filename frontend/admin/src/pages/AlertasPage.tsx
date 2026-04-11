import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
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
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
} from '@/components/ui/pagination'
import { AlertasTable } from '@/components/alertas/AlertasTable'
import { useAlertas } from '@/hooks/use-alertas'
import type { EstadoAlerta, NivelAlerta, OrigemAlerta } from '@/types/alertas'

const PAGE_SIZE = 20

export function AlertasPage() {
  const [estado, setEstado] = useState<EstadoAlerta | 'all'>('all')
  const [nivel, setNivel] = useState<NivelAlerta | 'all'>('all')
  const [origem, setOrigem] = useState<OrigemAlerta | 'all'>('all')
  const [page, setPage] = useState(1)

  const { data, loading, error, refetch } = useAlertas({
    estado: estado === 'all' ? undefined : estado,
    nivel: nivel === 'all' ? undefined : nivel,
    origem: origem === 'all' ? undefined : origem,
    page,
  })

  const totalPaginas = data ? Math.ceil(data.count / PAGE_SIZE) : 1

  function handleFilterChange(setter: (v: string) => void) {
    return (value: string) => {
      setter(value)
      setPage(1)
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Alertas</h1>

      <Card>
        <CardHeader>
          <CardTitle>Listagem de Alertas</CardTitle>
          <div className="flex flex-wrap gap-3 mt-2">
            <div className="flex items-center gap-2">
              <span className="text-sm text-muted-foreground">Origem:</span>
              <Select value={origem} onValueChange={handleFilterChange((v) => setOrigem(v as OrigemAlerta | 'all'))}>
                <SelectTrigger className="w-40">
                  <SelectValue placeholder="Todas" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todas</SelectItem>
                  <SelectItem value="provedor">Provedor</SelectItem>
                  <SelectItem value="interno">Interno</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-sm text-muted-foreground">Estado:</span>
              <Select value={estado} onValueChange={handleFilterChange((v) => setEstado(v as EstadoAlerta | 'all'))}>
                <SelectTrigger className="w-40">
                  <SelectValue placeholder="Todos" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todos</SelectItem>
                  <SelectItem value="ativo">Ativo</SelectItem>
                  <SelectItem value="resolvido">Resolvido</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-sm text-muted-foreground">Nivel:</span>
              <Select value={nivel} onValueChange={handleFilterChange((v) => setNivel(v as NivelAlerta | 'all'))}>
                <SelectTrigger className="w-40">
                  <SelectValue placeholder="Todos" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todos</SelectItem>
                  <SelectItem value="info">Info</SelectItem>
                  <SelectItem value="aviso">Aviso</SelectItem>
                  <SelectItem value="importante">Importante</SelectItem>
                  <SelectItem value="critico">Critico</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {error ? (
            <div className="text-center py-8 text-destructive">
              {error}{' '}
              <button
                onClick={() => void refetch()}
                className="underline hover:no-underline"
              >
                Tentar novamente
              </button>
            </div>
          ) : loading ? (
            <div className="text-center py-8 text-muted-foreground">
              Carregando alertas...
            </div>
          ) : (
            <AlertasTable alertas={data?.results ?? []} />
          )}
        </CardContent>
      </Card>

      {totalPaginas > 1 && (
        <Pagination>
          <PaginationContent>
            <PaginationItem>
              <PaginationPrevious
                href="#"
                text="Anterior"
                onClick={(e) => {
                  e.preventDefault()
                  if (page > 1) setPage(page - 1)
                }}
                aria-disabled={page <= 1}
                className={page <= 1 ? 'pointer-events-none opacity-50' : ''}
              />
            </PaginationItem>
            {Array.from({ length: totalPaginas }, (_, i) => i + 1).map((p) => (
              <PaginationItem key={p}>
                <PaginationLink
                  href="#"
                  isActive={p === page}
                  onClick={(e) => {
                    e.preventDefault()
                    setPage(p)
                  }}
                >
                  {p}
                </PaginationLink>
              </PaginationItem>
            ))}
            <PaginationItem>
              <PaginationNext
                href="#"
                text="Proximo"
                onClick={(e) => {
                  e.preventDefault()
                  if (page < totalPaginas) setPage(page + 1)
                }}
                aria-disabled={page >= totalPaginas}
                className={page >= totalPaginas ? 'pointer-events-none opacity-50' : ''}
              />
            </PaginationItem>
          </PaginationContent>
        </Pagination>
      )}
    </div>
  )
}
