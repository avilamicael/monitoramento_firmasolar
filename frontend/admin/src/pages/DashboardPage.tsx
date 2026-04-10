import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { EnergiaCards } from '@/components/dashboard/EnergiaCards'
import { AlertasCards } from '@/components/dashboard/AlertasCards'
import { PotenciaPieChart } from '@/components/dashboard/PotenciaPieChart'
import { RankingTable } from '@/components/dashboard/RankingTable'
import { GeracaoDiariaChart } from '@/components/dashboard/GeracaoDiariaChart'
import { AlertasCriticosTable } from '@/components/dashboard/AlertasCriticosTable'
import {
  useEnergiaResumo,
  useAlertasResumo,
  useAnalyticsPotencia,
  useAnalyticsRanking,
  useGeracaoDiaria,
} from '@/hooks/use-analytics'
import { useAlertas } from '@/hooks/use-alertas'

export function DashboardPage() {
  const energia = useEnergiaResumo()
  const alertasResumo = useAlertasResumo()
  const potencia = useAnalyticsPotencia()
  const ranking = useAnalyticsRanking()
  const geracao = useGeracaoDiaria(30)
  const alertasCriticos = useAlertas({ estado: 'ativo', nivel: 'critico' })

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

      {/* Linha 3 — Potencia media + Ranking lado a lado */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Potência Média por Fabricante</CardTitle>
            {potencia.error && (
              <CardDescription className="text-destructive">
                {potencia.error}{' '}
                <button
                  onClick={() => void potencia.refetch()}
                  className="underline hover:no-underline"
                >
                  Tentar novamente
                </button>
              </CardDescription>
            )}
          </CardHeader>
          <CardContent>
            {potencia.loading ? (
              <Skeleton className="h-[300px] w-full" />
            ) : (
              <div className="space-y-4">
                <div className="text-center">
                  <p className="text-sm text-muted-foreground">Potência média geral</p>
                  <p className="text-3xl font-bold">
                    {potencia.data?.media_geral_kw != null
                      ? `${potencia.data.media_geral_kw.toFixed(2)} kW`
                      : '--'}
                  </p>
                </div>
                <PotenciaPieChart data={potencia.data?.por_provedor ?? []} />
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Ranking Top 5 Fabricantes</CardTitle>
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
              <RankingTable ranking={(ranking.data?.ranking ?? []).slice(0, 5)} />
            )}
          </CardContent>
        </Card>
      </div>

      {/* Linha 4 — Gráfico de geração diária */}
      <Card>
        <CardHeader>
          <CardTitle>Geração de Energia (Últimos 30 dias)</CardTitle>
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

      {/* Linha 5 — Tabela de alertas críticos */}
      <Card>
        <CardHeader>
          <CardTitle>Alertas Críticos Ativos</CardTitle>
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
