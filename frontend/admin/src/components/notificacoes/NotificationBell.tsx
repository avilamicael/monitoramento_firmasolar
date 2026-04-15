import { BellIcon } from 'lucide-react'
import { Link } from 'react-router'

import { Button } from '@/components/ui/button'
import { useNotificacoesCount } from '@/hooks/use-notificacoes'

export function NotificationBell() {
  const { count } = useNotificacoesCount()
  const temNaoLidas = count > 0
  const label = count > 99 ? '99+' : String(count)

  return (
    <Button
      asChild
      variant="ghost"
      size="icon"
      aria-label={temNaoLidas ? `${count} notificações não lidas` : 'Notificações'}
      className="relative"
    >
      <Link to="/notificacoes">
        <BellIcon className="size-4" />
        {temNaoLidas && (
          <span
            className="absolute -top-0.5 -right-0.5 min-w-4 h-4 px-1 rounded-full bg-red-600 text-[10px] font-semibold text-white flex items-center justify-center"
          >
            {label}
          </span>
        )}
      </Link>
    </Button>
  )
}
