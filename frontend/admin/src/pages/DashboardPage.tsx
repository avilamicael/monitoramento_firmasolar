import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { EnergiaCards } from '@/components/dashboard/EnergiaCards'
import { AlertasCards } from '@/components/dashboard/AlertasCards'
import { FabricantePieChart } from '@/components/dashboard/FabricantePieChart'
import { UsinasPorCidadeChart } from '@/components/dashboard/UsinasPorCidadeChart'
import { GeracaoDiariaChart } from '@/components/dashboard/GeracaoDiariaChart'
import { AlertasCriticosTable } from '@/components/dashboard/AlertasCriticosTable'
import {
  useEnergiaResumo,
  useAlertasResumo,
  useAnalyticsRanking,
  useGeracaoDiaria,
} from '@/hooks/use-analytics'
import { useAlertas } from '@/hooks/use-alertas'
import { useUsinas } from '@/hooks/use-usinas'

export function DashboardPage() {
  const energia = useEnergiaResumo()
  const alertasResumo = useAlertasResumo()
  const ranking = useAnalyticsRanking()
  const geracao = useGeracaoDiaria(30)
  const alertasCriticos = useAlertas({ estado: 'ativo', nivel: 'critico' })
  const usinas = useUsinas()

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Dashboard</h1>

      {/* Linha 1 — Cards de energia */}
      <EnergiaCards
        data={energia.data}
        loading={energia.loading}
        error={energia.error}
        onRetry={energia.refetch}
      />

      {/* Linha 2 — Cards de alertas */}
      <AlertasCards
        data={alertasResumo.data}
        loading={alertasResumo.loading}
        error={alertasResumo.error}
        onRetry={alertasResumo.refetch}
      />

      {/* Linha 3 — Graficos lado a lado */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Inversores por Fabricante</CardTitle>
            {ranking.error && (
              <CardDescription className="text-destructive">
                {ranking.error}{' '}
                <button
                  onClick={() => void ranking.refetch()}
                  className="underline hover:no-underline"
                >
                  Tentar novamente
                </button>
              </CardDescription>
            )}
          </CardHeader>
          <CardContent>
            {ranking.loading ? (
              <Skeleton className="h-[300px] w-full" />
            ) : (
              <FabricantePieChart data={ranking.data?.ranking ?? []} />
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Usinas por Cidade</CardTitle>
            {usinas.error && (
              <CardDescription className="text-destructive">
                {usinas.error}{' '}
                <button
                  onClick={() => void usinas.refetch()}
                  className="underline hover:no-underline"
                >
                  Tentar novamente
                </button>
              </CardDescription>
            )}
          </CardHeader>
          <CardContent>
            {usinas.loading ? (
              <Skeleton className="h-[300px] w-full" />
            ) : (
              <UsinasPorCidadeChart usinas={usinas.data?.results ?? []} />
            )}
          </CardContent>
        </Card>
      </div>

      {/* Linha 4 — Grafico de geracao diaria */}
      <Card>
        <CardHeader>
          <CardTitle>Geracao de Energia (Ultimos 30 dias)</CardTitle>
        </CardHeader>
        <CardContent>
          <GeracaoDiariaChart
            data={geracao.data?.geracao ?? []}
            loading={geracao.loading}
            error={geracao.error}
            onRetry={geracao.refetch}
          />
        </CardContent>
      </Card>

      {/* Linha 5 — Tabela de alertas criticos */}
      <Card>
        <CardHeader>
          <CardTitle>Alertas Criticos Ativos</CardTitle>
          <CardDescription>
            Clique em um alerta para ver mais detalhes
          </CardDescription>
        </CardHeader>
        <CardContent>
          <AlertasCriticosTable
            alertas={alertasCriticos.data?.results ?? []}
            loading={alertasCriticos.loading}
            error={alertasCriticos.error}
            onRetry={alertasCriticos.refetch}
          />
        </CardContent>
      </Card>
    </div>
  )
}
