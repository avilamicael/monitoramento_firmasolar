import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import type { ProvedorRanking } from '@/types/analytics'

interface RankingTableProps {
  ranking: ProvedorRanking[]
  selectedProvedor: string | null
  onSelectProvedor: (provedor: string | null) => void
}

export function RankingTable({ ranking, selectedProvedor, onSelectProvedor }: RankingTableProps) {
  if (ranking.length === 0) {
    return (
      <p className="text-muted-foreground text-center py-8">
        Nenhum dado de ranking disponivel
      </p>
    )
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead className="w-12">#</TableHead>
          <TableHead>Provedor</TableHead>
          <TableHead className="text-right">Inversores Ativos</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {ranking.map((item, index) => (
          <TableRow
            key={item.provedor}
            onClick={() =>
              onSelectProvedor(item.provedor === selectedProvedor ? null : item.provedor)
            }
            className={
              item.provedor === selectedProvedor
                ? 'bg-muted'
                : 'cursor-pointer hover:bg-muted/50'
            }
          >
            <TableCell className="font-medium">{index + 1}</TableCell>
            <TableCell>{item.provedor}</TableCell>
            <TableCell className="text-right">{item.inversores_ativos}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}
