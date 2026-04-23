import { Link } from 'react-router'
import { Button } from '@/components/ui/button'
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from '@/components/ui/table'
import { StatusGarantiaBadge } from '@/components/usinas/StatusGarantiaBadge'
import type { UsinaResumo } from '@/types/usinas'

interface UsinasTableProps {
  usinas: UsinaResumo[]
  onEdit: (usina: UsinaResumo) => void
}

export function UsinasTable({ usinas, onEdit }: UsinasTableProps) {
  // Detecta nomes homônimos na lista — quando houver, mostramos o id do
  // provedor abaixo do nome para que o operador distinga cada planta.
  const nomesDuplicados = new Set<string>()
  const vistos = new Set<string>()
  for (const u of usinas) {
    if (vistos.has(u.nome)) {
      nomesDuplicados.add(u.nome)
    } else {
      vistos.add(u.nome)
    }
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Nome</TableHead>
          <TableHead>Provedor</TableHead>
          <TableHead>Capacidade</TableHead>
          <TableHead>Status Garantia</TableHead>
          <TableHead>Acoes</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {usinas.length === 0 ? (
          <TableRow>
            <TableCell colSpan={5} className="text-center text-muted-foreground">
              Nenhuma usina encontrada
            </TableCell>
          </TableRow>
        ) : (
          usinas.map((usina) => (
            <TableRow key={usina.id}>
              <TableCell>
                <Link
                  to={`/usinas/${usina.id}`}
                  className="font-medium text-primary hover:underline"
                >
                  {usina.nome}
                </Link>
                {nomesDuplicados.has(usina.nome) && (
                  <div className="text-xs text-muted-foreground">
                    #{usina.id_usina_provedor}
                  </div>
                )}
              </TableCell>
              <TableCell>{usina.provedor}</TableCell>
              <TableCell>{usina.capacidade_kwp} kWp</TableCell>
              <TableCell>
                <StatusGarantiaBadge status={usina.status_garantia} />
              </TableCell>
              <TableCell>
                <Button variant="outline" size="sm" onClick={() => onEdit(usina)}>
                  Editar
                </Button>
              </TableCell>
            </TableRow>
          ))
        )}
      </TableBody>
    </Table>
  )
}
