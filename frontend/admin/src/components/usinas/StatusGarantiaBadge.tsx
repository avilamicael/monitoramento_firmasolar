import { Badge } from '@/components/ui/badge'
import type { StatusGarantia } from '@/types/usinas'

interface StatusGarantiaBadgeProps {
  status: StatusGarantia
}

const CONFIG: Record<StatusGarantia, { label: string; className: string }> = {
  ativa: {
    label: 'Ativa',
    className: 'bg-green-100 text-green-800 hover:bg-green-100',
  },
  vencida: {
    label: 'Vencida',
    className: 'bg-red-100 text-red-800 hover:bg-red-100',
  },
  sem_garantia: {
    label: 'Sem Garantia',
    className: 'bg-gray-100 text-gray-600 hover:bg-gray-100',
  },
}

export function StatusGarantiaBadge({ status }: StatusGarantiaBadgeProps) {
  const config = CONFIG[status]
  return <Badge className={config.className}>{config.label}</Badge>
}
