import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import type { ProvedorPotencia } from '@/types/analytics'

const CORES = ['#8884d8', '#82ca9d', '#ffc658', '#ff7300', '#0088fe']

interface PotenciaPieChartProps {
  data: ProvedorPotencia[]
}

export function PotenciaPieChart({ data }: PotenciaPieChartProps) {
  // Filtrar provedores sem dados de potencia (media_kw null ou zero)
  const dadosFiltrados = data.filter((p) => p.media_kw !== null && p.media_kw > 0)

  if (dadosFiltrados.length === 0) {
    return (
      <p className="text-muted-foreground text-center py-8">
        Sem dados de potencia disponiveis
      </p>
    )
  }

  return (
    <ResponsiveContainer width="100%" height={300}>
      <PieChart>
        <Pie
          data={dadosFiltrados}
          dataKey="media_kw"
          nameKey="provedor"
          cx="50%"
          cy="50%"
          outerRadius={100}
          label
        >
          {dadosFiltrados.map((_, index) => (
            <Cell key={index} fill={CORES[index % CORES.length]} />
          ))}
        </Pie>
        <Tooltip
          formatter={(value) => {
            const kw = typeof value === 'number' ? value.toFixed(2) : String(value)
            return [kw + ' kW', 'Potencia media']
          }}
        />
        <Legend />
      </PieChart>
    </ResponsiveContainer>
  )
}
