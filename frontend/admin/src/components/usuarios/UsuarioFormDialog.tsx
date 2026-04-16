import { useEffect, useState } from 'react'
import { toast } from 'sonner'

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
import { extrairErroUsuario } from '@/hooks/use-usuarios'
import type { Usuario, UsuarioWrite } from '@/types/usuarios'

interface UsuarioFormDialogProps {
  usuario: Usuario | null
  open: boolean
  onClose: () => void
  onSubmit: (payload: UsuarioWrite | Partial<UsuarioWrite>, id: number | null) => Promise<void>
}

export function UsuarioFormDialog({
  usuario,
  open,
  onClose,
  onSubmit,
}: UsuarioFormDialogProps) {
  const isEditing = usuario !== null

  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [firstName, setFirstName] = useState('')
  const [lastName, setLastName] = useState('')
  const [isStaff, setIsStaff] = useState(false)
  const [isActive, setIsActive] = useState(true)
  const [password, setPassword] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (!open) return
    if (usuario) {
      setUsername(usuario.username)
      setEmail(usuario.email)
      setFirstName(usuario.first_name)
      setLastName(usuario.last_name)
      setIsStaff(usuario.is_staff)
      setIsActive(usuario.is_active)
      setPassword('')
    } else {
      setUsername('')
      setEmail('')
      setFirstName('')
      setLastName('')
      setIsStaff(false)
      setIsActive(true)
      setPassword('')
    }
  }, [usuario, open])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!username.trim()) {
      toast.error('Nome de usuário é obrigatório.')
      return
    }
    if (!isEditing && !password) {
      toast.error('Senha é obrigatória para novo usuário.')
      return
    }
    if (password && password.length < 6) {
      toast.error('Senha precisa ter pelo menos 6 caracteres.')
      return
    }

    const payload: UsuarioWrite = {
      username: username.trim(),
      email: email.trim(),
      first_name: firstName.trim(),
      last_name: lastName.trim(),
      is_staff: isStaff,
      is_active: isActive,
    }
    if (password) payload.password = password

    setSaving(true)
    try {
      await onSubmit(payload, usuario?.id ?? null)
      toast.success(isEditing ? 'Usuário atualizado.' : 'Usuário criado.')
      onClose()
    } catch (err) {
      toast.error(extrairErroUsuario(err, 'Erro ao salvar usuário.'))
    } finally {
      setSaving(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={(v) => { if (!v) onClose() }}>
      <DialogContent className="sm:max-w-md max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{isEditing ? `Editar — ${usuario?.username}` : 'Novo Usuário'}</DialogTitle>
          <DialogDescription>
            {isEditing ? 'Deixe a senha em branco para manter a atual.' : 'Preencha os dados do novo usuário.'}
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="username">Nome de usuário (login)</Label>
            <Input
              id="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="off"
              required
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="first_name">Nome</Label>
              <Input
                id="first_name"
                value={firstName}
                onChange={(e) => setFirstName(e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="last_name">Sobrenome</Label>
              <Input
                id="last_name"
                value={lastName}
                onChange={(e) => setLastName(e.target.value)}
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="email">E-mail</Label>
            <Input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="password">{isEditing ? 'Nova senha (opcional)' : 'Senha'}</Label>
            <Input
              id="password"
              type="password"
              autoComplete="new-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder={isEditing ? 'Em branco = manter atual' : 'Mínimo 6 caracteres'}
            />
          </div>

          <div className="flex items-center gap-4">
            <label className="flex items-center gap-2 text-sm cursor-pointer">
              <input
                type="checkbox"
                checked={isStaff}
                onChange={(e) => setIsStaff(e.target.checked)}
                className="size-4"
              />
              Administrador (staff)
            </label>
            <label className="flex items-center gap-2 text-sm cursor-pointer">
              <input
                type="checkbox"
                checked={isActive}
                onChange={(e) => setIsActive(e.target.checked)}
                className="size-4"
              />
              Ativo
            </label>
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose} disabled={saving}>
              Cancelar
            </Button>
            <Button type="submit" disabled={saving}>
              {saving ? 'Salvando...' : isEditing ? 'Atualizar' : 'Criar'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
