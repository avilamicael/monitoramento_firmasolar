import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'
import type { UsinaResumo } from '@/types/usinas'

interface UsinasPorCidadeChartProps {
  usinas: UsinaResumo[]
}

interface CidadeContagem {
  cidade: string
  quantidade: number
}

function agruparPorCidade(usinas: UsinaResumo[]): CidadeContagem[] {
  const contagem = new Map<string, number>()
  for (const usina of usinas) {
    const cidade = usina.cidade || 'Sem cidade'
    contagem.set(cidade, (contagem.get(cidade) ?? 0) + 1)
  }
  return Array.from(contagem.entries())
    .map(([cidade, quantidade]) => ({ cidade, quantidade }))
    .sort((a, b) => b.quantidade - a.quantidade)
}

export function UsinasPorCidadeChart({ usinas }: UsinasPorCidadeChartProps) {
  const dados = agruparPorCidade(usinas)

  if (dados.length === 0) {
    return (
      <p className="text-muted-foreground text-center py-8">
        Sem dados de cidades disponiveis
      </p>
    )
  }

  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={dados} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
        <XAxis
          dataKey="cidade"
          tick={{ fontSize: 12 }}
          className="text-muted-foreground"
        />
        <YAxis
          allowDecimals={false}
          tick={{ fontSize: 12 }}
          className="text-muted-foreground"
        />
        <Tooltip
          formatter={(value) => [value, 'Usinas']}
          contentStyle={{ borderRadius: '8px' }}
        />
        <Bar dataKey="quantidade" fill="#8884d8" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  )
}
