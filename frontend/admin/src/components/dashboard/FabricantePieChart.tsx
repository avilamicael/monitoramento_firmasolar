import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import type { PieLabelRenderProps } from 'recharts'
import type { ProvedorRanking } from '@/types/analytics'

const CORES = ['#8884d8', '#82ca9d', '#ffc658', '#ff7300', '#0088fe', '#d84888', '#88d8c4']

interface FabricantePieChartProps {
  data: ProvedorRanking[]
}

export function FabricantePieChart({ data }: FabricantePieChartProps) {
  if (data.length === 0) {
    return (
      <p className="text-muted-foreground text-center py-8">
        Sem dados de fabricantes disponiveis
      </p>
    )
  }

  return (
    <ResponsiveContainer width="100%" height={300}>
      <PieChart>
        <Pie
          data={data}
          dataKey="inversores_ativos"
          nameKey="provedor"
          cx="50%"
          cy="50%"
          outerRadius={100}
          label={(props: PieLabelRenderProps) => `${props.name ?? ''}: ${props.value ?? ''}`}
        >
          {data.map((_, index) => (
            <Cell key={index} fill={CORES[index % CORES.length]} />
          ))}
        </Pie>
        <Tooltip
          formatter={(value) => {
            const count = typeof value === 'number' ? value : Number(value)
            return [count, 'Inversores']
          }}
        />
        <Legend />
      </PieChart>
    </ResponsiveContainer>
  )
}
