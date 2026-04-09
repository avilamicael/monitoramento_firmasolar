export interface GarantiaUsina {
  id: string
  usina_id: string
  usina_nome: string
  data_inicio: string
  meses: number
  observacoes: string
  data_fim: string
  dias_restantes: number
  ativa: boolean
  criado_em: string
  atualizado_em: string
}

export interface GarantiaInput {
  data_inicio: string
  meses: number
  observacoes?: string
}

export interface PaginatedGarantias {
  count: number
  next: string | null
  previous: string | null
  results: GarantiaUsina[]
}
