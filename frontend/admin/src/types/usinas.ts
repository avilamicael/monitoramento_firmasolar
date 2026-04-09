export type StatusGarantia = 'ativa' | 'vencida' | 'sem_garantia'

export interface UsinaResumo {
  id: string
  nome: string
  provedor: string
  capacidade_kwp: number
  ativo: boolean
  status_garantia: StatusGarantia
  criado_em: string
  atualizado_em: string
}

export interface InversorResumo {
  id: string
  numero_serie: string
  modelo: string
  id_inversor_provedor: string
}

export interface SnapshotUsina {
  id: string
  coletado_em: string
  data_medicao: string
  potencia_kw: number
  energia_hoje_kwh: number
  energia_mes_kwh: number
  energia_total_kwh: number
  status: string
  qtd_inversores: number
  qtd_inversores_online: number
  qtd_alertas: number
}

export interface UsinaDetalhe {
  id: string
  nome: string
  provedor: string
  capacidade_kwp: number
  ativo: boolean
  fuso_horario: string
  endereco: string
  status_garantia: StatusGarantia
  ultimo_snapshot: SnapshotUsina | null
  inversores: InversorResumo[]
  criado_em: string
  atualizado_em: string
}

export interface PaginatedUsinas {
  count: number
  next: string | null
  previous: string | null
  results: UsinaResumo[]
}

export interface UsinaPatch {
  nome?: string
  capacidade_kwp?: number
}
