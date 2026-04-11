import { useState } from 'react'
import { SearchIcon } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
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
import type { EstadoAlerta, NivelAlerta } from '@/types/alertas'

const PAGE_SIZE = 20

export function AlertasPage() {
  const [estado, setEstado] = useState<EstadoAlerta | 'all'>('ativo')
  const [nivel, setNivel] = useState<NivelAlerta | 'all'>('all')
  const [provedor, setProvedor] = useState<string>('all')
  const [categoria, setCategoria] = useState<string>('all')
  const [busca, setBusca] = useState('')
  const [buscaDebounced, setBuscaDebounced] = useState('')
  const [debounceTimer, setDebounceTimer] = useState<ReturnType<typeof setTimeout> | null>(null)
  const [page, setPage] = useState(1)

  const { data, loading, error, refetch } = useAlertas({
    estado: estado === 'all' ? undefined : estado,
    nivel: nivel === 'all' ? undefined : nivel,
    provedor: provedor === 'all' ? undefined : provedor,
    categoria: categoria === 'all' ? undefined : categoria,
    busca: buscaDebounced || undefined,
    page,
  })

  const totalPaginas = data ? Math.ceil(data.count / PAGE_SIZE) : 1

  function handleFilterChange(setter: (v: string) => void) {
    return (value: string) => {
      setter(value)
      setPage(1)
    }
  }

  function handleBuscaChange(value: string) {
    setBusca(value)
    if (debounceTimer) clearTimeout(debounceTimer)
    const timer = setTimeout(() => {
      setBuscaDebounced(value)
      setPage(1)
    }, 400)
    setDebounceTimer(timer)
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Alertas</h1>

      <Card>
        <CardHeader>
          <CardTitle>Listagem de Alertas</CardTitle>
          <div className="space-y-3 mt-2">
            <div className="relative max-w-sm">
              <SearchIcon className="absolute left-2.5 top-2.5 size-4 text-muted-foreground" />
              <Input
                placeholder="Buscar por usina, mensagem ou equipamento..."
                value={busca}
                onChange={(e) => handleBuscaChange(e.target.value)}
                className="pl-9"
              />
            </div>
            <div className="flex flex-wrap gap-3">
              <div className="flex items-center gap-2">
                <span className="text-sm text-muted-foreground">Estado:</span>
                <Select value={estado} onValueChange={handleFilterChange((v) => setEstado(v as EstadoAlerta | 'all'))}>
                  <SelectTrigger className="w-36">
                    <SelectValue />
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
                  <SelectTrigger className="w-36">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Todos</SelectItem>
                    <SelectItem value="critico">Critico</SelectItem>
                    <SelectItem value="importante">Importante</SelectItem>
                    <SelectItem value="aviso">Aviso</SelectItem>
                    <SelectItem value="info">Info</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-sm text-muted-foreground">Provedor:</span>
                <Select value={provedor} onValueChange={handleFilterChange((v) => setProvedor(v))}>
                  <SelectTrigger className="w-36">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Todos</SelectItem>
                    <SelectItem value="solis">Solis</SelectItem>
                    <SelectItem value="hoymiles">Hoymiles</SelectItem>
                    <SelectItem value="fusionsolar">FusionSolar</SelectItem>
                    <SelectItem value="auxsol">AuxSol</SelectItem>
                    <SelectItem value="solarman">Solarman</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-sm text-muted-foreground">Categoria:</span>
                <Select value={categoria} onValueChange={handleFilterChange((v) => setCategoria(v))}>
                  <SelectTrigger className="w-44">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Todas</SelectItem>
                    <SelectItem value="tensao_zero">Tensao zero</SelectItem>
                    <SelectItem value="sobretensao">Sobretensao</SelectItem>
                    <SelectItem value="corrente_baixa">Corrente baixa</SelectItem>
                    <SelectItem value="sem_geracao_diurna">Sem geracao (dia)</SelectItem>
                    <SelectItem value="sem_comunicacao">Sem comunicacao</SelectItem>
                  </SelectContent>
                </Select>
              </div>
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
            <>
              <AlertasTable alertas={data?.results ?? []} />
              <div className="mt-2 text-sm text-muted-foreground">
                {data?.count ?? 0} alerta{(data?.count ?? 0) !== 1 ? 's' : ''} encontrado{(data?.count ?? 0) !== 1 ? 's' : ''}
              </div>
            </>
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
            {Array.from({ length: Math.min(totalPaginas, 5) }, (_, i) => {
              const start = Math.max(1, Math.min(page - 2, totalPaginas - 4))
              return start + i
            }).map((p) => (
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
