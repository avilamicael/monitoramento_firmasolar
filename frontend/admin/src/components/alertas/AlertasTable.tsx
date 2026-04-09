import { Link } from 'react-router'
import { Badge } from '@/components/ui/badge'
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from '@/components/ui/table'
import type { AlertaResumo, EstadoAlerta, NivelAlerta } from '@/types/alertas'

interface AlertasTableProps {
  alertas: AlertaResumo[]
  onSelectAlerta?: (id: string) => void
}

const NIVEL_CONFIG: Record<NivelAlerta, { label: string; className?: string; variant?: 'destructive' | 'secondary' | 'outline' }> = {
  critico: { label: 'Crítico', variant: 'destructive' },
  importante: { label: 'Importante', className: 'bg-orange-100 text-orange-800 hover:bg-orange-100' },
  aviso: { label: 'Aviso', variant: 'secondary' },
  info: { label: 'Info', variant: 'outline' },
}

const ESTADO_LABEL: Record<EstadoAlerta, string> = {
  ativo: 'Ativo',
  em_atendimento: 'Em atendimento',
  resolvido: 'Resolvido',
}

export function AlertasTable({ alertas, onSelectAlerta }: AlertasTableProps) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Usina</TableHead>
          <TableHead>Mensagem</TableHead>
          <TableHead>Nível</TableHead>
          <TableHead>Estado</TableHead>
          <TableHead>Com Garantia</TableHead>
          <TableHead>Data</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {alertas.length === 0 ? (
          <TableRow>
            <TableCell colSpan={6} className="text-center text-muted-foreground">
              Nenhum alerta encontrado
            </TableCell>
          </TableRow>
        ) : (
          alertas.map((alerta) => {
            const nivelConfig = NIVEL_CONFIG[alerta.nivel]
            return (
              <TableRow key={alerta.id} onClick={() => onSelectAlerta?.(alerta.id)}>
                <TableCell>
                  <Link
                    to={`/alertas/${alerta.id}`}
                    className="font-medium text-primary hover:underline"
                  >
                    {alerta.usina_nome}
                  </Link>
                </TableCell>
                <TableCell className="max-w-xs truncate">{alerta.mensagem}</TableCell>
                <TableCell>
                  {nivelConfig.className ? (
                    <Badge className={nivelConfig.className}>{nivelConfig.label}</Badge>
                  ) : (
                    <Badge variant={nivelConfig.variant}>{nivelConfig.label}</Badge>
                  )}
                </TableCell>
                <TableCell>{ESTADO_LABEL[alerta.estado]}</TableCell>
                <TableCell>
                  {alerta.com_garantia ? (
                    <Badge className="bg-green-100 text-green-800 hover:bg-green-100">Sim</Badge>
                  ) : (
                    <Badge variant="secondary">Não</Badge>
                  )}
                </TableCell>
                <TableCell>
                  {new Date(alerta.inicio).toLocaleDateString('pt-BR')}
                </TableCell>
              </TableRow>
            )
          })
        )}
      </TableBody>
    </Table>
  )
}
