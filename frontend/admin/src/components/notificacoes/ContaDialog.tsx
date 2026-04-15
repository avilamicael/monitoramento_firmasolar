import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { useAuth } from '@/contexts/auth'

interface ContaDialogProps {
  open: boolean
  onClose: () => void
}

export function ContaDialog({ open, onClose }: ContaDialogProps) {
  const { user } = useAuth()

  return (
    <Dialog open={open} onOpenChange={(v) => { if (!v) onClose() }}>
      <DialogContent className="sm:max-w-sm">
        <DialogHeader>
          <DialogTitle>Minha Conta</DialogTitle>
          <DialogDescription>Informações do seu usuário no sistema.</DialogDescription>
        </DialogHeader>
        <dl className="grid grid-cols-1 gap-3 text-sm mt-2">
          <div>
            <dt className="text-muted-foreground font-medium">Nome</dt>
            <dd className="mt-0.5">{user?.name || '—'}</dd>
          </div>
          <div>
            <dt className="text-muted-foreground font-medium">Email</dt>
            <dd className="mt-0.5">{user?.email || '—'}</dd>
          </div>
        </dl>
      </DialogContent>
    </Dialog>
  )
}
