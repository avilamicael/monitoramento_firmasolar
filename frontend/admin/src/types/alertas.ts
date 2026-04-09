export type EstadoAlerta = 'ativo' | 'em_atendimento' | 'resolvido'
export type NivelAlerta = 'info' | 'aviso' | 'importante' | 'critico'

export interface AlertaResumo {
  id: string
  usina: string
  usina_nome: string
  mensagem: string
  nivel: NivelAlerta
  estado: EstadoAlerta
  inicio: string
  fim: string | null
  com_garantia: boolean
  criado_em: string
  atualizado_em: string
}

export interface AlertaDetalhe extends AlertaResumo {
  catalogo_alarme: number | null
  id_alerta_provedor: string
  equipamento_sn: string
  sugestao: string
  anotacoes: string
}

export interface AlertaPatch {
  estado?: EstadoAlerta
  anotacoes?: string
}

export interface PaginatedAlertas {
  count: number
  next: string | null
  previous: string | null
  results: AlertaResumo[]
}
