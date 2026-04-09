import { AlertTriangleIcon, InfoIcon, WrenchIcon } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import type { AlertasResumo } from '@/types/analytics'

interface AlertasCardsProps {
  data: AlertasResumo | null
  loading: boolean
  error: string | null
  onRetry: () => void
}

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
      <Card className="border-red-200 dark:border-red-900">
        <CardHeader className="flex flex-row items-center justify-between pb-2">
          <CardTitle className="text-sm font-medium text-red-600 dark:text-red-400">
            Alertas Criticos
          </CardTitle>
          <AlertTriangleIcon className="size-4 text-red-600 dark:text-red-400" />
        </CardHeader>
        <CardContent>
          {loading ? (
            <Skeleton className="h-8 w-12" />
          ) : (
            <p className="text-2xl font-bold text-red-600 dark:text-red-400">
              {data?.critico ?? 0}
            </p>
          )}
        </CardContent>
      </Card>

      <Card className="border-blue-200 dark:border-blue-900">
        <CardHeader className="flex flex-row items-center justify-between pb-2">
          <CardTitle className="text-sm font-medium text-blue-600 dark:text-blue-400">
            Alertas Info
          </CardTitle>
          <InfoIcon className="size-4 text-blue-600 dark:text-blue-400" />
        </CardHeader>
        <CardContent>
          {loading ? (
            <Skeleton className="h-8 w-12" />
          ) : (
            <p className="text-2xl font-bold text-blue-600 dark:text-blue-400">
              {data?.info ?? 0}
            </p>
          )}
        </CardContent>
      </Card>

      <Card className="border-amber-200 dark:border-amber-900">
        <CardHeader className="flex flex-row items-center justify-between pb-2">
          <CardTitle className="text-sm font-medium text-amber-600 dark:text-amber-400">
            Em Atendimento
          </CardTitle>
          <WrenchIcon className="size-4 text-amber-600 dark:text-amber-400" />
        </CardHeader>
        <CardContent>
          {loading ? (
            <Skeleton className="h-8 w-12" />
          ) : (
            <p className="text-2xl font-bold text-amber-600 dark:text-amber-400">
              {data?.em_atendimento ?? 0}
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
