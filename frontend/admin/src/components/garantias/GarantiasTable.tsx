import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import type { GarantiaUsina } from '@/types/garantias'

interface GarantiasTableProps {
  garantias: GarantiaUsina[]
  onEdit: (garantia: GarantiaUsina) => void
}

function formatarData(dataStr: string): string {
  return new Date(dataStr + 'T00:00:00').toLocaleDateString('pt-BR')
}

interface StatusBadgeProps {
  garantia: GarantiaUsina
}

function StatusBadge({ garantia }: StatusBadgeProps) {
  const isVencendoLogo = garantia.ativa && garantia.dias_restantes < 30

  if (isVencendoLogo) {
    return <Badge className="bg-red-100 text-red-800">Vencendo</Badge>
  }

  if (garantia.ativa) {
    return <Badge className="bg-green-100 text-green-800">Ativa</Badge>
  }

  return <Badge className="bg-red-100 text-red-800">Vencida</Badge>
}

export function GarantiasTable({ garantias, onEdit }: GarantiasTableProps) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Usina</TableHead>
          <TableHead>Data Inicio</TableHead>
          <TableHead>Data Fim</TableHead>
          <TableHead>Meses</TableHead>
          <TableHead>Dias Restantes</TableHead>
          <TableHead>Status</TableHead>
          <TableHead>Acoes</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {garantias.length === 0 ? (
          <TableRow>
            <TableCell colSpan={7} className="text-center text-muted-foreground">
              Nenhuma garantia encontrada
            </TableCell>
          </TableRow>
        ) : (
          garantias.map((garantia) => {
            const isVencendoLogo = garantia.ativa && garantia.dias_restantes < 30
            return (
              <TableRow
                key={garantia.id}
                className={isVencendoLogo ? 'bg-red-50' : undefined}
              >
                <TableCell className="font-medium">{garantia.usina_nome}</TableCell>
                <TableCell>{formatarData(garantia.data_inicio)}</TableCell>
                <TableCell>{formatarData(garantia.data_fim)}</TableCell>
                <TableCell>{garantia.meses}</TableCell>
                <TableCell>
                  <span className="mr-2">{garantia.dias_restantes} dias</span>
                  {isVencendoLogo && (
                    <Badge className="bg-red-100 text-red-800">Vencendo</Badge>
                  )}
                </TableCell>
                <TableCell>
                  <StatusBadge garantia={garantia} />
                </TableCell>
                <TableCell>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => onEdit(garantia)}
                  >
                    Editar
                  </Button>
                </TableCell>
              </TableRow>
            )
          })
        )}
      </TableBody>
    </Table>
  )
}
