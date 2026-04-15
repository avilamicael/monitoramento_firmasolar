import { Link, useParams } from 'react-router'
import {
  ArrowLeftIcon,
  Loader2Icon,
  ZapIcon,
  BatteryChargingIcon,
  ThermometerIcon,
  ActivityIcon,
  AlertTriangleIcon,
} from 'lucide-react'
import { useUsina } from '@/hooks/use-usinas'
import { useAlertas } from '@/hooks/use-alertas'
import { StatusGarantiaBadge } from '@/components/usinas/StatusGarantiaBadge'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from '@/components/ui/table'
import type { InversorResumo } from '@/types/usinas'
import { CATEGORIA_LABELS } from '@/types/alertas'

const PROVEDOR_LABELS: Record<string, string> = {
  solis: 'Solis Cloud',
  hoymiles: 'Hoymiles S-Cloud',
  fusionsolar: 'Huawei FusionSolar',
  auxsol: 'AuxSol Cloud',
  solarman: 'Solarman Pro',
}

function formatarNumero(valor: number | null | undefined, decimais = 2): string {
  if (valor === null || valor === undefined) return '—'
  return valor.toLocaleString('pt-BR', { minimumFractionDigits: decimais, maximumFractionDigits: decimais })
}

function formatarEnergia(kwh: number | null | undefined): string {
  if (kwh === null || kwh === undefined) return '—'
  if (kwh >= 1000) return `${formatarNumero(kwh / 1000)} MWh`
  return `${formatarNumero(kwh)} kWh`
}

/**
 * Normaliza strings_mppt de diferentes provedores para exibição uniforme.
 * Formatos conhecidos:
 *   Solis/AuxSol/Solarman: {string1: 16.94} — potência em W
 *   Hoymiles: {1: {tensao: 19.8, corrente: 0.01}} — objeto com tensão e corrente
 *   FusionSolar: {mppt_1_cap: 2696.49} — energia acumulada em kWh
 */
function parsearMppt(mppt: Record<string, unknown> | null | undefined): { nome: string; valor: string }[] {
  if (!mppt) return []
  const resultado: { nome: string; valor: string }[] = []

  for (const [chave, val] of Object.entries(mppt)) {
    if (val === null || val === undefined) continue

    // Formato objeto (Hoymiles): {tensao: 19.8, corrente: 0.01}
    if (typeof val === 'object' && val !== null && !Array.isArray(val)) {
      const obj = val as Record<string, number | null>
      const tensao = `${formatarNumero(obj.tensao ?? 0, 1)} V`
      const corrente = `${formatarNumero(obj.corrente ?? 0, 2)} A`
      const partes = `${tensao} / ${corrente}`
      if (partes) {
        resultado.push({ nome: `Placa ${chave}`, valor: partes })
      }
      continue
    }

    // Formato numérico (Solis, AuxSol, Solarman, FusionSolar)
    const num = Number(val)
    if (isNaN(num)) continue

    // FusionSolar: mppt_X_cap → energia em kWh
    if (chave.includes('cap')) {
      const idx = chave.replace('mppt_', '').replace('_cap', '')
      resultado.push({ nome: `Placa ${idx}`, valor: num === 0 ? 'Sem geracao' : `${formatarNumero(num, 1)} kWh` })
      continue
    }

    // Outros: potência em W
    const idx = chave.replace('string', '')
    resultado.push({ nome: `Placa ${idx}`, valor: num === 0 ? 'Sem geracao' : `${formatarNumero(num, 1)} W` })
  }

  return resultado
}

function estadoBadge(estado: string) {
  if (estado === 'normal') return <Badge variant="default" className="bg-green-600">Online</Badge>
  if (estado === 'aviso') return <Badge variant="secondary" className="bg-yellow-500 text-black">Aviso</Badge>
  return <Badge variant="destructive">Offline</Badge>
}

const NIVEL_CONFIG: Record<string, { label: string; className?: string; variant?: 'destructive' | 'secondary' | 'outline' }> = {
  critico: { label: 'Critico', variant: 'destructive' },
  importante: { label: 'Importante', className: 'bg-orange-100 text-orange-800 hover:bg-orange-100' },
  aviso: { label: 'Aviso', variant: 'secondary' },
  info: { label: 'Info', variant: 'outline' },
}

export function UsinaDetalhePage() {
  const { id } = useParams<{ id: string }>()
  const { data, loading, error } = useUsina(id!)
  const alertas = useAlertas({ usina: id })

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

  const snap = data.ultimo_snapshot
  const inversoresOnline = data.inversores.filter(
    (inv) => inv.ultimo_snapshot?.estado === 'normal'
  ).length

  return (
    <div className="space-y-6">
      <Link
        to="/usinas"
        className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeftIcon className="size-4" />
        Voltar para Usinas
      </Link>

      {/* Header com nome e status */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold">{data.nome}</h1>
          <p className="text-sm text-muted-foreground mt-1">
            {PROVEDOR_LABELS[data.provedor] || data.provedor} &middot; {data.capacidade_kwp} kWp
          </p>
        </div>
        <StatusGarantiaBadge status={data.status_garantia} />
      </div>

      {/* Cards de resumo em tempo real */}
      {snap && (
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          <Card>
            <CardContent className="pt-4 pb-3">
              <div className="flex items-center gap-2">
                <ZapIcon className="size-4 text-yellow-500" />
                <span className="text-xs text-muted-foreground">Potencia Atual</span>
              </div>
              <p className="text-2xl font-bold mt-1">{formatarNumero(snap.potencia_kw)} kW</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4 pb-3">
              <div className="flex items-center gap-2">
                <BatteryChargingIcon className="size-4 text-green-500" />
                <span className="text-xs text-muted-foreground">Energia Hoje</span>
              </div>
              <p className="text-2xl font-bold mt-1">{formatarEnergia(snap.energia_hoje_kwh)}</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4 pb-3">
              <div className="flex items-center gap-2">
                <ActivityIcon className="size-4 text-blue-500" />
                <span className="text-xs text-muted-foreground">Energia Mes</span>
              </div>
              <p className="text-2xl font-bold mt-1">{formatarEnergia(snap.energia_mes_kwh)}</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4 pb-3">
              <div className="flex items-center gap-2">
                <ActivityIcon className="size-4 text-purple-500" />
                <span className="text-xs text-muted-foreground">Energia Total</span>
              </div>
              <p className="text-2xl font-bold mt-1">{formatarEnergia(snap.energia_total_kwh)}</p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Informacoes da usina + status da coleta */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Informacoes da Usina</CardTitle>
          </CardHeader>
          <CardContent>
            <dl className="grid grid-cols-1 gap-y-3 sm:grid-cols-2 gap-x-8">
              <div>
                <dt className="text-xs text-muted-foreground">Endereco</dt>
                <dd className="text-sm font-medium">{data.endereco || '—'}</dd>
              </div>
              <div>
                <dt className="text-xs text-muted-foreground">Cidade</dt>
                <dd className="text-sm font-medium">{data.cidade || '—'}</dd>
              </div>
              <div>
                <dt className="text-xs text-muted-foreground">Telefone</dt>
                <dd className="text-sm font-medium">{data.telefone || '—'}</dd>
              </div>
              <div>
                <dt className="text-xs text-muted-foreground">Fuso Horario</dt>
                <dd className="text-sm font-medium">{data.fuso_horario}</dd>
              </div>
              <div>
                <dt className="text-xs text-muted-foreground">Capacidade</dt>
                <dd className="text-sm font-medium">{data.capacidade_kwp} kWp</dd>
              </div>
              <div>
                <dt className="text-xs text-muted-foreground">Provedor</dt>
                <dd className="text-sm font-medium">{PROVEDOR_LABELS[data.provedor] || data.provedor}</dd>
              </div>
            </dl>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Status da Coleta</CardTitle>
          </CardHeader>
          <CardContent>
            {snap ? (
              <dl className="grid grid-cols-1 gap-y-3 sm:grid-cols-2 gap-x-8">
                <div>
                  <dt className="text-xs text-muted-foreground">Inversores Online</dt>
                  <dd className="text-sm font-medium">
                    {inversoresOnline}/{data.inversores.length}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs text-muted-foreground">Alertas Ativos</dt>
                  <dd className="text-sm font-medium">
                    {snap.qtd_alertas > 0 ? (
                      <span className="text-destructive flex items-center gap-1">
                        <AlertTriangleIcon className="size-3.5" />
                        {snap.qtd_alertas}
                      </span>
                    ) : (
                      <span className="text-green-600">Nenhum</span>
                    )}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs text-muted-foreground">Status</dt>
                  <dd className="text-sm font-medium">{snap.status || '—'}</dd>
                </div>
                <div>
                  <dt className="text-xs text-muted-foreground">Ultima Coleta</dt>
                  <dd className="text-sm font-medium">
                    {new Date(snap.coletado_em).toLocaleString('pt-BR')}
                  </dd>
                </div>
              </dl>
            ) : (
              <p className="text-sm text-muted-foreground">Nenhum snapshot coletado ainda</p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Tabela de inversores com dados eletricos */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">
            Inversores ({data.inversores.length})
          </CardTitle>
        </CardHeader>
        <CardContent>
          {data.inversores.length === 0 ? (
            <p className="text-sm text-muted-foreground">Nenhum inversor associado</p>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Status</TableHead>
                    <TableHead>Numero de Serie</TableHead>
                    <TableHead>Modelo</TableHead>
                    <TableHead className="text-right">Potencia (kW)</TableHead>
                    <TableHead className="text-right">Energia Hoje</TableHead>
                    <TableHead className="text-right">Energia Total</TableHead>
                    <TableHead className="text-right">Tensao AC (V)</TableHead>
                    <TableHead className="text-right">Corrente AC (A)</TableHead>
                    <TableHead className="text-right">Tensao DC (V)</TableHead>
                    <TableHead className="text-right">Corrente DC (A)</TableHead>
                    <TableHead className="text-right">Freq. (Hz)</TableHead>
                    <TableHead className="text-right">Temp. (°C)</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.inversores.map((inversor) => (
                    <InversorRow key={inversor.id} inversor={inversor} />
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Placas solares por inversor */}
      {data.inversores.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Placas Solares (por inversor)</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
              {data.inversores.map((inv) => {
                const placas = parsearMppt(inv.ultimo_snapshot?.strings_mppt)
                return (
                  <div key={inv.id} className="rounded-lg border p-3 space-y-2">
                    <p className="text-sm font-medium">{inv.numero_serie}</p>
                    {placas.length > 0 ? (
                      <div className="space-y-1">
                        {placas.map((item) => (
                          <div key={item.nome} className="flex justify-between text-xs">
                            <span className="text-muted-foreground">{item.nome}</span>
                            <span className="font-medium">{item.valor}</span>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-xs text-muted-foreground">Sem dados de geracao no momento</p>
                    )}
                  </div>
                )
              })}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Historico de alertas da usina */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <AlertTriangleIcon className="size-4" />
            Historico de Alertas
          </CardTitle>
        </CardHeader>
        <CardContent>
          {alertas.loading ? (
            <p className="text-sm text-muted-foreground">Carregando alertas...</p>
          ) : (alertas.data?.results?.length ?? 0) === 0 ? (
            <p className="text-sm text-muted-foreground">Nenhum alerta registrado para esta usina</p>
          ) : (
            <div className="space-y-2">
              {alertas.data!.results.map((alerta) => {
                const nivelCfg = NIVEL_CONFIG[alerta.nivel] || NIVEL_CONFIG.aviso
                const resolvido = alerta.estado === 'resolvido'
                return (
                  <Link
                    key={alerta.id}
                    to={`/alertas/${alerta.id}`}
                    className={`block rounded-lg border p-3 hover:bg-muted/50 transition-colors ${resolvido ? 'opacity-60' : ''}`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="space-y-1 flex-1">
                        <div className="flex items-center gap-2">
                          {nivelCfg.className ? (
                            <Badge className={`${nivelCfg.className} text-xs`}>{nivelCfg.label}</Badge>
                          ) : (
                            <Badge variant={nivelCfg.variant} className="text-xs">{nivelCfg.label}</Badge>
                          )}
                          {resolvido ? (
                            <Badge variant="outline" className="text-xs">Resolvido</Badge>
                          ) : (
                            <Badge variant="destructive" className="text-xs">Ativo</Badge>
                          )}
                          {alerta.categoria_efetiva && (
                            <span className="text-xs text-muted-foreground">
                              {CATEGORIA_LABELS[alerta.categoria_efetiva] || alerta.categoria_efetiva}
                            </span>
                          )}
                        </div>
                        <p className="text-sm">{alerta.mensagem}</p>
                      </div>
                      <span className="text-xs text-muted-foreground whitespace-nowrap">
                        {new Date(alerta.inicio).toLocaleString('pt-BR')}
                      </span>
                    </div>
                  </Link>
                )
              })}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

function InversorRow({ inversor }: { inversor: InversorResumo }) {
  const snap = inversor.ultimo_snapshot

  return (
    <TableRow>
      <TableCell>{snap ? estadoBadge(snap.estado) : <Badge variant="outline">—</Badge>}</TableCell>
      <TableCell className="font-mono text-xs">{inversor.numero_serie}</TableCell>
      <TableCell>{inversor.modelo}</TableCell>
      <TableCell className="text-right">{snap ? formatarNumero(snap.pac_kw, 3) : '—'}</TableCell>
      <TableCell className="text-right">{snap ? formatarEnergia(snap.energia_hoje_kwh) : '—'}</TableCell>
      <TableCell className="text-right">{snap ? formatarEnergia(snap.energia_total_kwh) : '—'}</TableCell>
      <TableCell className="text-right">{snap ? formatarNumero(snap.tensao_ac_v, 1) : '—'}</TableCell>
      <TableCell className="text-right">{snap ? formatarNumero(snap.corrente_ac_a, 2) : '—'}</TableCell>
      <TableCell className="text-right">{snap ? formatarNumero(snap.tensao_dc_v, 1) : '—'}</TableCell>
      <TableCell className="text-right">{snap ? formatarNumero(snap.corrente_dc_a, 2) : '—'}</TableCell>
      <TableCell className="text-right">{snap ? formatarNumero(snap.frequencia_hz, 2) : '—'}</TableCell>
      <TableCell className="text-right">
        {snap?.temperatura_c != null ? (
          <span className={snap.temperatura_c > 60 ? 'text-destructive font-medium' : ''}>
            <ThermometerIcon className="size-3 inline mr-0.5" />
            {formatarNumero(snap.temperatura_c, 1)}
          </span>
        ) : '—'}
      </TableCell>
    </TableRow>
  )
}
