import { useState } from 'react'
import { toast } from 'sonner'
import {
  CheckCircle2Icon,
  Loader2Icon,
  PencilIcon,
  PlusIcon,
  ShieldCheckIcon,
  Trash2Icon,
  XCircleIcon,
} from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { UsuarioFormDialog } from '@/components/usuarios/UsuarioFormDialog'
import { extrairErroUsuario, useUsuarios } from '@/hooks/use-usuarios'
import type { Usuario, UsuarioWrite } from '@/types/usuarios'

function formatarData(iso: string | null): string {
  if (!iso) return 'Nunca'
  return new Date(iso).toLocaleString('pt-BR', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

export function UsuariosPage() {
  const { data, loading, error, criar, atualizar, remover } = useUsuarios()
  const [formTarget, setFormTarget] = useState<Usuario | null | 'novo'>(null)
  const [acaoId, setAcaoId] = useState<number | null>(null)

  async function handleSubmit(payload: UsuarioWrite | Partial<UsuarioWrite>, id: number | null) {
    if (id) await atualizar(id, payload)
    else await criar(payload as UsuarioWrite)
  }

  async function handleRemover(u: Usuario) {
    if (!window.confirm(`Remover o usuário "${u.username}"? Esta ação é irreversível.`)) return
    setAcaoId(u.id)
    try {
      await remover(u.id)
      toast.success('Usuário removido.')
    } catch (err) {
      toast.error(extrairErroUsuario(err, 'Erro ao remover usuário.'))
    } finally {
      setAcaoId(null)
    }
  }

  if (error) {
    return (
      <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">
        {error}
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Gestão de Usuários</h1>
          <p className="text-sm text-muted-foreground">
            Crie, edite ou remova usuários do sistema. Administradores (staff) têm acesso às páginas de gestão.
          </p>
        </div>
        <Button onClick={() => setFormTarget('novo')}>
          <PlusIcon className="size-4 mr-1" />
          Novo usuário
        </Button>
      </div>

      {loading ? (
        <div className="space-y-2">
          {[0, 1, 2].map((i) => <Skeleton key={i} className="h-12 w-full" />)}
        </div>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Usuário</TableHead>
              <TableHead>Nome</TableHead>
              <TableHead>E-mail</TableHead>
              <TableHead>Perfil</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Último login</TableHead>
              <TableHead className="text-right">Ações</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {(data ?? []).length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} className="text-center text-muted-foreground">
                  Nenhum usuário cadastrado
                </TableCell>
              </TableRow>
            ) : (
              (data ?? []).map((u) => {
                const em = acaoId === u.id
                return (
                  <TableRow key={u.id}>
                    <TableCell className="font-medium">{u.username}</TableCell>
                    <TableCell>{[u.first_name, u.last_name].filter(Boolean).join(' ') || '—'}</TableCell>
                    <TableCell className="text-sm">{u.email || '—'}</TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1">
                        {u.is_superuser && (
                          <Badge className="bg-purple-100 text-purple-800 gap-1 text-xs">
                            <ShieldCheckIcon className="size-3" />
                            Super
                          </Badge>
                        )}
                        {u.is_staff && !u.is_superuser && (
                          <Badge className="bg-blue-100 text-blue-800 text-xs">Admin</Badge>
                        )}
                        {!u.is_staff && (
                          <Badge variant="secondary" className="text-xs">Operador</Badge>
                        )}
                      </div>
                    </TableCell>
                    <TableCell>
                      {u.is_active ? (
                        <Badge className="bg-green-100 text-green-800 gap-1 text-xs">
                          <CheckCircle2Icon className="size-3" />
                          Ativo
                        </Badge>
                      ) : (
                        <Badge variant="secondary" className="gap-1 text-xs">
                          <XCircleIcon className="size-3" />
                          Inativo
                        </Badge>
                      )}
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {formatarData(u.last_login)}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-1">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => setFormTarget(u)}
                          disabled={em}
                        >
                          <PencilIcon className="size-3.5" />
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleRemover(u)}
                          disabled={em}
                        >
                          {em ? (
                            <Loader2Icon className="size-3.5 animate-spin" />
                          ) : (
                            <Trash2Icon className="size-3.5 text-destructive" />
                          )}
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                )
              })
            )}
          </TableBody>
        </Table>
      )}

      <UsuarioFormDialog
        usuario={formTarget && formTarget !== 'novo' ? formTarget : null}
        open={formTarget !== null}
        onClose={() => setFormTarget(null)}
        onSubmit={handleSubmit}
      />
    </div>
  )
}
