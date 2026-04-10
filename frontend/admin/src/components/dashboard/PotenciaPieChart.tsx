import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import type { ProvedorPotencia } from '@/types/analytics'

const CORES = ['#8884d8', '#82ca9d', '#ffc658', '#ff7300', '#0088fe']

interface PotenciaPieChartProps {
  data: ProvedorPotencia[]
}

export function PotenciaPieChart({ data }: PotenciaPieChartProps) {
  const dadosFiltrados = data.filter((p) => p.energia_hoje_kwh > 0)

  if (dadosFiltrados.length === 0) {
    return (
      <p className="text-muted-foreground text-center py-8">
        Sem dados de geração disponíveis
      </p>
    )
  }

  return (
    <ResponsiveContainer width="100%" height={300}>
      <PieChart>
        <Pie
          data={dadosFiltrados}
          dataKey="energia_hoje_kwh"
          nameKey="provedor"
          cx="50%"
          cy="50%"
          outerRadius={100}
          label={({ name, value }) => `${name}: ${Number(value).toFixed(0)} kWh`}
        >
          {dadosFiltrados.map((_, index) => (
            <Cell key={index} fill={CORES[index % CORES.length]} />
          ))}
        </Pie>
        <Tooltip
          formatter={(value) => {
            const kwh = typeof value === 'number' ? value.toFixed(1) : String(value)
            return [kwh + ' kWh', 'Energia hoje']
          }}
        />
        <Legend />
      </PieChart>
    </ResponsiveContainer>
  )
}
