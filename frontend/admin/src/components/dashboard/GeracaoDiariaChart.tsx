import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
  CartesianGrid,
} from 'recharts'
import { Skeleton } from '@/components/ui/skeleton'
import type { GeracaoDiariaItem } from '@/types/analytics'

interface GeracaoDiariaChartProps {
  data: GeracaoDiariaItem[]
  loading: boolean
  error: string | null
  onRetry: () => void
}

function formatarData(dia: string): string {
  const [, mes, d] = dia.split('-')
  return `${d}/${mes}`
}

function usarMWh(data: GeracaoDiariaItem[]): boolean {
  return data.some((item) => item.energia_kwh >= 1000)
}

export function GeracaoDiariaChart({ data, loading, error, onRetry }: GeracaoDiariaChartProps) {
  if (error) {
    return (
      <p className="text-sm text-destructive">
        {error}{' '}
        <button onClick={onRetry} className="underline hover:no-underline">
          Tentar novamente
        </button>
      </p>
    )
  }

  if (loading) {
    return <Skeleton className="h-[300px] w-full" />
  }

  if (data.length === 0) {
    return (
      <p className="text-muted-foreground text-center py-8">
        Sem dados de geracao disponíveis
      </p>
    )
  }

  const converterMWh = usarMWh(data)
  const unidade = converterMWh ? 'MWh' : 'kWh'
  const dadosFormatados = data.map((item) => ({
    dia: formatarData(item.dia),
    energia: converterMWh ? Number((item.energia_kwh / 1000).toFixed(2)) : Number(item.energia_kwh.toFixed(2)),
    usinas: item.usinas_coletadas,
  }))

  return (
    <ResponsiveContainer width="100%" height={300}>
      <AreaChart data={dadosFormatados} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
        <defs>
          <linearGradient id="gradienteEnergia" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#8884d8" stopOpacity={0.3} />
            <stop offset="95%" stopColor="#8884d8" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
        <XAxis
          dataKey="dia"
          tick={{ fontSize: 11 }}
          className="text-muted-foreground"
        />
        <YAxis
          tick={{ fontSize: 12 }}
          className="text-muted-foreground"
          tickFormatter={(value) => `${value} ${unidade}`}
        />
        <Tooltip
          formatter={(value, name) => {
            if (name === 'energia') return [`${Number(value).toLocaleString('pt-BR')} ${unidade}`, `Geração do dia`]
            return [value, name]
          }}
          labelFormatter={(label) => `Data: ${label}`}
          contentStyle={{ borderRadius: '8px', fontSize: '13px' }}
        />
        <Legend
          formatter={() => `Energia gerada (${unidade})`}
          wrapperStyle={{ fontSize: '12px', paddingTop: '8px' }}
        />
        <Area
          type="monotone"
          dataKey="energia"
          name="energia"
          stroke="#8884d8"
          fill="url(#gradienteEnergia)"
          strokeWidth={2}
        />
      </AreaChart>
    </ResponsiveContainer>
  )
}
