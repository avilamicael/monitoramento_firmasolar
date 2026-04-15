export type EstadoAlerta = 'ativo' | 'resolvido'
export type NivelAlerta = 'info' | 'aviso' | 'importante' | 'critico'
export type OrigemAlerta = 'provedor' | 'interno'
export type CategoriaAlerta =
  | 'tensao_zero'
  | 'sobretensao'
  | 'corrente_baixa'
  | 'sem_geracao_diurna'
  | 'sem_comunicacao'
  | 'geracao_abaixo'
  | 'geracao_acima'
  | 'temperatura_alta'
  | 'garantia_expirando'
  | 'outro'

export interface AlertaResumo {
  id: string
  usina: string
  usina_nome: string
  origem: OrigemAlerta
  categoria: string
  categoria_efetiva: string
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
  usina_provedor: string
  usina_id_provedor: string
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

// Labels centralizados. Inclui:
// - categorias de alertas internos (Alerta.categoria)
// - categorias do catálogo (CatalogoAlarme.tipo) usadas no fallback de alertas do provedor
export const CATEGORIA_LABELS: Record<string, string> = {
  tensao_zero: 'Tensão zero',
  sobretensao: 'Sobretensão',
  corrente_baixa: 'Corrente baixa',
  sem_geracao_diurna: 'Sem geração (dia)',
  sem_comunicacao: 'Sem comunicação',
  geracao_abaixo: 'Geração abaixo',
  geracao_acima: 'Geração acima',
  temperatura_alta: 'Temperatura alta',
  garantia_expirando: 'Garantia expirando',
  outro: 'Outro',
  equipamento: 'Equipamento',
  comunicacao: 'Comunicação',
  rede_eletrica: 'Rede elétrica',
  sistema_desligado: 'Sistema desligado',
  preventivo: 'Preventivo',
}
