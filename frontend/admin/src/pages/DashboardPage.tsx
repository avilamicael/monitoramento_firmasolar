import { useState } from 'react'
import { Loader2Icon } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { PotenciaPieChart } from '@/components/dashboard/PotenciaPieChart'
import { RankingTable } from '@/components/dashboard/RankingTable'
import { useAnalyticsPotencia } from '@/hooks/use-analytics'
import { useAnalyticsRanking } from '@/hooks/use-analytics'

export function DashboardPage() {
  // selectedProvedor sera passado ao MapaUsinas no Plan 02
  const [selectedProvedor, setSelectedProvedor] = useState<string | null>(null)

  const {
    data: potenciaData,
    loading: potenciaLoading,
    error: potenciaError,
    refetch: refetchPotencia,
  } = useAnalyticsPotencia()

  const {
    data: rankingData,
    loading: rankingLoading,
    error: rankingError,
    refetch: refetchRanking,
  } = useAnalyticsRanking()

  const isLoading = potenciaLoading || rankingLoading

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Dashboard</h1>

      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2Icon className="size-6 animate-spin text-muted-foreground" />
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Grafico de pizza: potencia media por fabricante */}
          <Card>
            <CardHeader>
              <CardTitle>Potencia Media por Fabricante</CardTitle>
              {potenciaError ? (
                <CardDescription className="text-destructive">
                  {potenciaError}{' '}
                  <button
                    onClick={() => void refetchPotencia()}
                    className="underline hover:no-underline"
                  >
                    Tentar novamente
                  </button>
                </CardDescription>
              ) : (
                <CardDescription>
                  {potenciaData?.media_geral_kw != null
                    ? `Potencia media geral: ${potenciaData.media_geral_kw.toFixed(2)} kW`
                    : 'Sem dados de potencia geral'}
                </CardDescription>
              )}
            </CardHeader>
            <CardContent>
              <PotenciaPieChart data={potenciaData?.por_provedor ?? []} />
            </CardContent>
          </Card>

          {/* Tabela de ranking top 5 fabricantes */}
          <Card>
            <CardHeader>
              <CardTitle>Top 5 Fabricantes</CardTitle>
              {rankingError ? (
                <CardDescription className="text-destructive">
                  {rankingError}{' '}
                  <button
                    onClick={() => void refetchRanking()}
                    className="underline hover:no-underline"
                  >
                    Tentar novamente
                  </button>
                </CardDescription>
              ) : (
                <CardDescription>
                  {selectedProvedor
                    ? `Filtrado por: ${selectedProvedor} — clique novamente para remover filtro`
                    : 'Clique em um fabricante para filtrar o mapa'}
                </CardDescription>
              )}
            </CardHeader>
            <CardContent>
              <RankingTable
                ranking={rankingData?.ranking ?? []}
                selectedProvedor={selectedProvedor}
                onSelectProvedor={setSelectedProvedor}
              />
            </CardContent>
          </Card>
        </div>
      )}

      {/* MapaUsinas sera adicionado no Plan 02 */}
    </div>
  )
}
