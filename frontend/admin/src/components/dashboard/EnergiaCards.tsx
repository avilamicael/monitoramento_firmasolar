import { ZapIcon, DollarSignIcon } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { formatarEnergia, formatarMoeda } from '@/lib/format'
import type { EnergiaResumo } from '@/types/analytics'

interface EnergiaCardsProps {
  data: EnergiaResumo | null
  loading: boolean
  error: string | null
  onRetry: () => void
}

const CUSTO_KWH = 0.88

export function EnergiaCards({ data, loading, error, onRetry }: EnergiaCardsProps) {
  if (error) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
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
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">
            Energia Total Gerada
          </CardTitle>
          <ZapIcon className="size-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          {loading ? (
            <Skeleton className="h-8 w-36" />
          ) : (
            <>
              <p className="text-2xl font-bold">
                {data ? formatarEnergia(data.energia_total_kwh) : '--'}
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                Soma da energia total acumulada de todas as usinas ativas
              </p>
            </>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">
            Valor Economizado
          </CardTitle>
          <DollarSignIcon className="size-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          {loading ? (
            <Skeleton className="h-8 w-36" />
          ) : (
            <>
              <p className="text-2xl font-bold">
                {data ? formatarMoeda(data.energia_total_kwh * CUSTO_KWH) : '--'}
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                Energia total × R$ 0,88/kWh
              </p>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
