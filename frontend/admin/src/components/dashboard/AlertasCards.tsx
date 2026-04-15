import { AlertTriangleIcon, AlertCircleIcon, BellIcon } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import type { AlertasResumo } from '@/types/analytics'

interface AlertasCardsProps {
  data: AlertasResumo | null
  loading: boolean
  error: string | null
  onRetry: () => void
}

interface CardConfig {
  titulo: string
  campo: keyof Pick<AlertasResumo, 'critico' | 'importante' | 'aviso'>
  icone: typeof AlertTriangleIcon
  cor: string
  borda: string
}

const CARDS: CardConfig[] = [
  {
    titulo: 'Alertas Críticos',
    campo: 'critico',
    icone: AlertTriangleIcon,
    cor: 'text-red-600 dark:text-red-400',
    borda: 'border-red-200 dark:border-red-900',
  },
  {
    titulo: 'Alertas Importantes',
    campo: 'importante',
    icone: AlertCircleIcon,
    cor: 'text-orange-600 dark:text-orange-400',
    borda: 'border-orange-200 dark:border-orange-900',
  },
  {
    titulo: 'Alertas de Aviso',
    campo: 'aviso',
    icone: BellIcon,
    cor: 'text-amber-600 dark:text-amber-400',
    borda: 'border-amber-200 dark:border-amber-900',
  },
]

export function AlertasCards({ data, loading, error, onRetry }: AlertasCardsProps) {
  if (error) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardContent className="py-6">
            <p className="text-sm text-destructive">
              {error}{' '}
              <button onClick={onRetry} className="underline hover:no-underline">
                Tentar novamente
              </button>
            </p>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      {CARDS.map(({ titulo, campo, icone: Icon, cor, borda }) => (
        <Card key={campo} className={borda}>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className={`text-sm font-medium ${cor}`}>{titulo}</CardTitle>
            <Icon className={`size-4 ${cor}`} />
          </CardHeader>
          <CardContent>
            {loading ? (
              <Skeleton className="h-8 w-12" />
            ) : (
              <p className={`text-2xl font-bold ${cor}`}>{data?.[campo] ?? 0}</p>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  )
}
