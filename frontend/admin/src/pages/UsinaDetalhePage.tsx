import { Link, useParams } from 'react-router'
import { ArrowLeftIcon, Loader2Icon } from 'lucide-react'
import { useUsina } from '@/hooks/use-usinas'
import { StatusGarantiaBadge } from '@/components/usinas/StatusGarantiaBadge'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from '@/components/ui/table'

export function UsinaDetalhePage() {
  const { id } = useParams<{ id: string }>()
  const { data, loading, error } = useUsina(id!)

  if (loading) {
    return (
      <div className="flex justify-center py-8">
        <Loader2Icon className="size-6 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (error) {
    return <div className="py-8 text-center text-destructive">{error}</div>
  }

  if (data === null) {
    return <div className="py-8 text-center text-muted-foreground">Usina nao encontrada</div>
  }

  return (
    <div className="space-y-6">
      <Link
        to="/usinas"
        className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeftIcon className="size-4" />
        Voltar para Usinas
      </Link>

      {/* Card principal */}
      <Card>
        <CardHeader>
          <CardTitle>{data.nome}</CardTitle>
        </CardHeader>
        <CardContent>
          <dl className="grid grid-cols-1 gap-x-8 gap-y-3 lg:grid-cols-2">
            <div>
              <dt className="text-xs text-muted-foreground">Provedor</dt>
              <dd className="text-sm font-medium">{data.provedor}</dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground">Capacidade</dt>
              <dd className="text-sm font-medium">{data.capacidade_kwp} kWp</dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground">Status Garantia</dt>
              <dd className="mt-0.5">
                <StatusGarantiaBadge status={data.status_garantia} />
              </dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground">Endereco</dt>
              <dd className="text-sm font-medium">{data.endereco || '—'}</dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground">Fuso Horario</dt>
              <dd className="text-sm font-medium">{data.fuso_horario}</dd>
            </div>
          </dl>
        </CardContent>
      </Card>

      {/* Card ultimo snapshot */}
      <Card>
        <CardHeader>
          <CardTitle>Ultimo Snapshot</CardTitle>
        </CardHeader>
        <CardContent>
          {data.ultimo_snapshot === null ? (
            <p className="text-sm text-muted-foreground">Nenhum snapshot coletado ainda</p>
          ) : (
            <dl className="grid grid-cols-1 gap-x-8 gap-y-3 lg:grid-cols-2">
              <div>
                <dt className="text-xs text-muted-foreground">Potencia</dt>
                <dd className="text-sm font-medium">{data.ultimo_snapshot?.potencia_kw} kW</dd>
              </div>
              <div>
                <dt className="text-xs text-muted-foreground">Energia Hoje</dt>
                <dd className="text-sm font-medium">{data.ultimo_snapshot?.energia_hoje_kwh} kWh</dd>
              </div>
              <div>
                <dt className="text-xs text-muted-foreground">Energia Mes</dt>
                <dd className="text-sm font-medium">{data.ultimo_snapshot?.energia_mes_kwh} kWh</dd>
              </div>
              <div>
                <dt className="text-xs text-muted-foreground">Energia Total</dt>
                <dd className="text-sm font-medium">{data.ultimo_snapshot?.energia_total_kwh} kWh</dd>
              </div>
              <div>
                <dt className="text-xs text-muted-foreground">Inversores Online</dt>
                <dd className="text-sm font-medium">
                  {data.ultimo_snapshot?.qtd_inversores_online}/{data.ultimo_snapshot?.qtd_inversores}
                </dd>
              </div>
              <div>
                <dt className="text-xs text-muted-foreground">Alertas</dt>
                <dd className="text-sm font-medium">{data.ultimo_snapshot?.qtd_alertas}</dd>
              </div>
              <div className="lg:col-span-2">
                <dt className="text-xs text-muted-foreground">Coletado em</dt>
                <dd className="text-sm font-medium">
                  {new Date(data.ultimo_snapshot?.coletado_em ?? '').toLocaleString('pt-BR')}
                </dd>
              </div>
            </dl>
          )}
        </CardContent>
      </Card>

      {/* Tabela de inversores */}
      <div className="space-y-2">
        <h2 className="text-base font-medium">Inversores ({data.inversores.length})</h2>
        {data.inversores.length === 0 ? (
          <p className="text-sm text-muted-foreground">Nenhum inversor associado</p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Numero de Serie</TableHead>
                <TableHead>Modelo</TableHead>
                <TableHead>ID Provedor</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.inversores.map((inversor) => (
                <TableRow key={inversor.id}>
                  <TableCell>{inversor.numero_serie}</TableCell>
                  <TableCell>{inversor.modelo}</TableCell>
                  <TableCell>{inversor.id_inversor_provedor}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </div>
    </div>
  )
}
