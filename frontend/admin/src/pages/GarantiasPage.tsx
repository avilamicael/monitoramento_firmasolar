import { useState, useEffect } from 'react'
import { Loader2Icon, PlusIcon, PencilIcon, SearchIcon } from 'lucide-react'
import { useUsinas } from '@/hooks/use-usinas'
import { useGarantias } from '@/hooks/use-garantias'
import { GarantiaFormDialog } from '@/components/garantias/GarantiaFormDialog'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  Pagination,
  PaginationContent,
  PaginationItem,
  PaginationNext,
  PaginationPrevious,
} from '@/components/ui/pagination'
import type { StatusGarantia } from '@/types/usinas'
import type { GarantiaUsina } from '@/types/garantias'

interface FormTarget {
  usina_id: string
  usina_nome: string
  garantia: GarantiaUsina | null
}

function formatarData(dataStr: string): string {
  return new Date(dataStr + 'T00:00:00').toLocaleDateString('pt-BR')
}

export function GarantiasPage() {
  const [statusFilter, setStatusFilter] = useState('')
  const [provedorFilter, setProvedorFilter] = useState('')
  const [ativoFilter, setAtivoFilter] = useState<'all' | 'true' | 'false'>('all')
  const [searchTerm, setSearchTerm] = useState('')
  const [searchInput, setSearchInput] = useState('')
  const [page, setPage] = useState(1)
  const [formTarget, setFormTarget] = useState<FormTarget | null>(null)

  // Debounce para a busca
  useEffect(() => {
    const timer = setTimeout(() => {
      setSearchTerm(searchInput)
      setPage(1) // Reset para primeira página quando buscar
    }, 500)
    return () => clearTimeout(timer)
  }, [searchInput])

  // Buscar usinas filtradas
  const { data: usinasData, loading: usinasLoading, error: usinasError, refetch: refetchUsinas } = useUsinas({
    status_garantia: (statusFilter as StatusGarantia) || undefined,
    provedor: provedorFilter || undefined,
    ativo: ativoFilter === 'all' ? undefined : ativoFilter === 'true',
    nome: searchTerm || undefined,
    page,
  })

  // Buscar todas as garantias para cruzar com usinas
  const { data: garantiasData, refetch: refetchGarantias } = useGarantias({})

  // Mapa de garantias por usina_id para lookup rápido
  const garantiasPorUsina = new Map<string, GarantiaUsina>()
  if (garantiasData?.results) {
    for (const g of garantiasData.results) {
      garantiasPorUsina.set(g.usina_id, g)
    }
  }

  const totalPages = Math.ceil((usinasData?.count ?? 0) / 20)

  function handleStatusFilterChange(value: string) {
    setStatusFilter(value === 'all' ? '' : value)
    setPage(1)
  }

  function handleProvedorFilterChange(value: string) {
    setProvedorFilter(value === 'all' ? '' : value)
    setPage(1)
  }

  function handleAtivoFilterChange(value: string) {
    setAtivoFilter(value as 'all' | 'true' | 'false')
    setPage(1)
  }

  function handleClearFilters() {
    setStatusFilter('')
    setProvedorFilter('')
    setAtivoFilter('all')
    setSearchInput('')
    setSearchTerm('')
    setPage(1)
  }

  function handleSuccess() {
    setFormTarget(null)
    void refetchUsinas()
    void refetchGarantias()
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Gestão de Garantias</h1>
      </div>

      {/* Barra de busca */}
      <div className="relative">
        <SearchIcon className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          type="text"
          placeholder="Buscar usinas por nome..."
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          className="pl-10"
        />
      </div>

      {/* Filtros */}
      <div className="flex flex-wrap items-center gap-3">
        <span className="text-sm text-muted-foreground">Filtrar por:</span>

        {/* Filtro de Status da Garantia */}
        <Select value={statusFilter || 'all'} onValueChange={handleStatusFilterChange}>
          <SelectTrigger className="w-48">
            <SelectValue placeholder="Status da Garantia" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todos os Status</SelectItem>
            <SelectItem value="ativa">Com garantia ativa</SelectItem>
            <SelectItem value="vencida">Garantia vencida</SelectItem>
            <SelectItem value="sem_garantia">Sem garantia</SelectItem>
          </SelectContent>
        </Select>

        {/* Filtro de Provedor */}
        <Select value={provedorFilter || 'all'} onValueChange={handleProvedorFilterChange}>
          <SelectTrigger className="w-48">
            <SelectValue placeholder="Provedor" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todos os Provedores</SelectItem>
            <SelectItem value="solis">Solis</SelectItem>
            <SelectItem value="hoymiles">Hoymiles</SelectItem>
            <SelectItem value="fusionsolar">FusionSolar</SelectItem>
            <SelectItem value="auxsol">AuxSol</SelectItem>
            <SelectItem value="solarman">Solarman</SelectItem>
          </SelectContent>
        </Select>

        {/* Filtro de Status Ativo */}
        <Select value={ativoFilter} onValueChange={handleAtivoFilterChange}>
          <SelectTrigger className="w-48">
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todas as Usinas</SelectItem>
            <SelectItem value="true">Usinas Ativas</SelectItem>
            <SelectItem value="false">Usinas Inativas</SelectItem>
          </SelectContent>
        </Select>

        {/* Botão Limpar Filtros */}
        {(statusFilter || provedorFilter || ativoFilter !== 'all' || searchInput) && (
          <Button
            variant="outline"
            size="sm"
            onClick={handleClearFilters}
          >
            Limpar Filtros
          </Button>
        )}
      </div>

      {usinasLoading ? (
        <div className="flex justify-center py-8">
          <Loader2Icon className="size-6 animate-spin text-muted-foreground" />
        </div>
      ) : usinasError ? (
        <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">
          {usinasError}
        </div>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Usina</TableHead>
              <TableHead>Provedor</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Data Início</TableHead>
              <TableHead>Data Fim</TableHead>
              <TableHead>Dias Restantes</TableHead>
              <TableHead>Meses</TableHead>
              <TableHead>Ações</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {(usinasData?.results ?? []).length === 0 ? (
              <TableRow>
                <TableCell colSpan={8} className="text-center text-muted-foreground">
                  Nenhuma usina encontrada
                </TableCell>
              </TableRow>
            ) : (
              (usinasData?.results ?? []).map((usina) => {
                const garantia = garantiasPorUsina.get(usina.id)
                const isVencendo = garantia?.ativa && (garantia?.dias_restantes ?? 0) < 30

                return (
                  <TableRow
                    key={usina.id}
                    className={isVencendo ? 'bg-red-50' : undefined}
                  >
                    <TableCell className="font-medium">{usina.nome}</TableCell>
                    <TableCell>{usina.provedor}</TableCell>
                    <TableCell>
                      {usina.status_garantia === 'ativa' && (
                        <Badge className="bg-green-100 text-green-800">
                          {isVencendo ? 'Vencendo' : 'Ativa'}
                        </Badge>
                      )}
                      {usina.status_garantia === 'vencida' && (
                        <Badge className="bg-red-100 text-red-800">Vencida</Badge>
                      )}
                      {usina.status_garantia === 'sem_garantia' && (
                        <Badge variant="secondary">Sem garantia</Badge>
                      )}
                    </TableCell>
                    <TableCell>
                      {garantia ? formatarData(garantia.data_inicio) : '—'}
                    </TableCell>
                    <TableCell>
                      {garantia ? formatarData(garantia.data_fim) : '—'}
                    </TableCell>
                    <TableCell>
                      {garantia ? (
                        <span className={isVencendo ? 'font-medium text-red-600' : ''}>
                          {garantia.dias_restantes} dias
                        </span>
                      ) : '—'}
                    </TableCell>
                    <TableCell>{garantia?.meses ?? '—'}</TableCell>
                    <TableCell>
                      {garantia ? (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => setFormTarget({
                            usina_id: usina.id,
                            usina_nome: usina.nome,
                            garantia,
                          })}
                        >
                          <PencilIcon className="size-3.5 mr-1" />
                          Editar
                        </Button>
                      ) : (
                        <Button
                          variant="default"
                          size="sm"
                          onClick={() => setFormTarget({
                            usina_id: usina.id,
                            usina_nome: usina.nome,
                            garantia: null,
                          })}
                        >
                          <PlusIcon className="size-3.5 mr-1" />
                          Adicionar
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                )
              })
            )}
          </TableBody>
        </Table>
      )}

      {!usinasLoading && !usinasError && totalPages > 1 && (
        <div className="flex items-center justify-between">
          <span className="text-sm text-muted-foreground">
            Página {page} de {totalPages}
          </span>
          <Pagination>
            <PaginationContent>
              <PaginationItem>
                <PaginationPrevious
                  text="Anterior"
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  aria-disabled={!usinasData?.previous}
                  className={!usinasData?.previous ? 'pointer-events-none opacity-50' : ''}
                />
              </PaginationItem>
              <PaginationItem>
                <PaginationNext
                  text="Próxima"
                  onClick={() => setPage((p) => p + 1)}
                  aria-disabled={!usinasData?.next}
                  className={!usinasData?.next ? 'pointer-events-none opacity-50' : ''}
                />
              </PaginationItem>
            </PaginationContent>
          </Pagination>
        </div>
      )}

      <GarantiaFormDialog
        garantia={formTarget?.garantia ?? null}
        usinaId={formTarget?.usina_id ?? null}
        usinaNome={formTarget?.usina_nome ?? null}
        open={!!formTarget}
        onClose={() => setFormTarget(null)}
        onSuccess={handleSuccess}
      />
    </div>
  )
}
