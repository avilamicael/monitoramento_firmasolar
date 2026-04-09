import { useState } from 'react'
import { Loader2Icon, XIcon } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { PotenciaPieChart } from '@/components/dashboard/PotenciaPieChart'
import { RankingTable } from '@/components/dashboard/RankingTable'
import { MapaUsinas } from '@/components/dashboard/MapaUsinas'
import { useAnalyticsPotencia, useAnalyticsRanking, useAnalyticsMapa } from '@/hooks/use-analytics'

export function DashboardPage() {
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

  const {
    data: mapaData,
    loading: mapaLoading,
    error: mapaError,
    refetch: refetchMapa,
  } = useAnalyticsMapa()

  const isLoading = potenciaLoading || rankingLoading || mapaLoading

  const usinasFiltradas = selectedProvedor
    ? (mapaData ?? []).filter((u) => u.provedor === selectedProvedor)
    : (mapaData ?? [])

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Dashboard</h1>

      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2Icon className="size-6 animate-spin text-muted-foreground" />
        </div>
      ) : (
        <>
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

          {/* Mapa de usinas */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Mapa de Usinas</CardTitle>
                {selectedProvedor && (
                  <div className="flex items-center gap-2">
                    <Badge variant="secondary">
                      Filtrando: {selectedProvedor}
                    </Badge>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setSelectedProvedor(null)}
                      className="h-6 w-6 p-0"
                      aria-label="Remover filtro"
                    >
                      <XIcon className="size-4" />
                    </Button>
                  </div>
                )}
              </div>
              {mapaError && (
                <CardDescription className="text-destructive">
                  {mapaError}{' '}
                  <button
                    onClick={() => void refetchMapa()}
                    className="underline hover:no-underline"
                  >
                    Tentar novamente
                  </button>
                </CardDescription>
              )}
            </CardHeader>
            <CardContent>
              <MapaUsinas usinas={usinasFiltradas} />
            </CardContent>
          </Card>
        </>
      )}
    </div>
  )
}
