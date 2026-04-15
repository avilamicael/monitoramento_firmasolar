import { useState } from 'react'
import { Link } from 'react-router'
import { BellIcon, CheckCheckIcon } from 'lucide-react'
import { toast } from 'sonner'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Pagination,
  PaginationContent,
  PaginationItem,
  PaginationNext,
  PaginationPrevious,
} from '@/components/ui/pagination'
import { useNotificacoes } from '@/hooks/use-notificacoes'
import type { NivelNotificacao, Notificacao } from '@/types/notificacoes'

const NIVEL_CLASSES: Record<NivelNotificacao, string> = {
  critico: 'bg-red-100 text-red-800',
  importante: 'bg-orange-100 text-orange-800',
  aviso: 'bg-amber-100 text-amber-800',
  info: 'bg-blue-100 text-blue-800',
}

const NIVEL_LABEL: Record<NivelNotificacao, string> = {
  critico: 'Crítico',
  importante: 'Importante',
  aviso: 'Aviso',
  info: 'Info',
}

function formatarDataHora(iso: string): string {
  return new Date(iso).toLocaleString('pt-BR', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

export function NotificacoesPage() {
  const [apenasNaoLidas, setApenasNaoLidas] = useState(false)
  const [page, setPage] = useState(1)
  const { data, loading, error, marcarLida, marcarTodasLidas } = useNotificacoes({
    apenasNaoLidas,
    page,
  })

  async function handleMarcarTodas() {
    try {
      await marcarTodasLidas()
      toast.success('Todas as notificações marcadas como lidas.')
    } catch {
      toast.error('Erro ao marcar notificações.')
    }
  }

  async function handleClicar(n: Notificacao) {
    if (!n.lida) {
      try { await marcarLida(n.id) } catch { /* ignore */ }
    }
  }

  const totalPages = Math.ceil((data?.count ?? 0) / 20)

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Notificações</h1>
          <p className="text-sm text-muted-foreground">
            Eventos recentes do sistema — alertas, garantias e avisos operacionais.
          </p>
        </div>
        <Button onClick={handleMarcarTodas} variant="outline" size="sm">
          <CheckCheckIcon className="size-4 mr-1" />
          Marcar todas como lidas
        </Button>
      </div>

      <div className="flex items-center gap-2">
        <Button
          variant={!apenasNaoLidas ? 'default' : 'outline'}
          size="sm"
          onClick={() => { setApenasNaoLidas(false); setPage(1) }}
        >
          Todas
        </Button>
        <Button
          variant={apenasNaoLidas ? 'default' : 'outline'}
          size="sm"
          onClick={() => { setApenasNaoLidas(true); setPage(1) }}
        >
          Não lidas
        </Button>
      </div>

      {error && (
        <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-3 text-sm text-destructive">
          {error}
        </div>
      )}

      {loading ? (
        <div className="space-y-2">
          {[0, 1, 2].map((i) => <Skeleton key={i} className="h-20 w-full" />)}
        </div>
      ) : (data?.results ?? []).length === 0 ? (
        <div className="rounded-lg border border-dashed p-12 text-center text-muted-foreground">
          <BellIcon className="size-10 mx-auto mb-2 opacity-40" />
          <p>Nenhuma notificação {apenasNaoLidas ? 'não lida' : ''} no momento.</p>
        </div>
      ) : (
        <div className="space-y-2">
          {(data?.results ?? []).map((n) => {
            const conteudo = (
              <div className={`rounded-lg border p-3 transition-colors ${n.lida ? 'opacity-70' : 'bg-accent/30'}`}>
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap mb-1">
                      <Badge className={`text-xs ${NIVEL_CLASSES[n.nivel]}`}>
                        {NIVEL_LABEL[n.nivel]}
                      </Badge>
                      {!n.lida && (
                        <Badge variant="outline" className="text-xs">Nova</Badge>
                      )}
                      {n.apenas_staff && (
                        <Badge variant="secondary" className="text-xs">Staff</Badge>
                      )}
                      <span className="text-xs text-muted-foreground">
                        {formatarDataHora(n.criado_em)}
                      </span>
                    </div>
                    <p className="font-medium truncate">{n.titulo}</p>
                    <p className="text-sm text-muted-foreground mt-1 line-clamp-2">
                      {n.mensagem}
                    </p>
                  </div>
                </div>
              </div>
            )

            return n.link ? (
              <Link
                key={n.id}
                to={n.link}
                onClick={() => handleClicar(n)}
                className="block hover:opacity-90"
              >
                {conteudo}
              </Link>
            ) : (
              <div key={n.id} onClick={() => handleClicar(n)} className="cursor-pointer">
                {conteudo}
              </div>
            )
          })}
        </div>
      )}

      {!loading && totalPages > 1 && (
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
                  aria-disabled={!data?.previous}
                  className={!data?.previous ? 'pointer-events-none opacity-50' : ''}
                />
              </PaginationItem>
              <PaginationItem>
                <PaginationNext
                  text="Próxima"
                  onClick={() => setPage((p) => p + 1)}
                  aria-disabled={!data?.next}
                  className={!data?.next ? 'pointer-events-none opacity-50' : ''}
                />
              </PaginationItem>
            </PaginationContent>
          </Pagination>
        </div>
      )}
    </div>
  )
}
