export type StatusGarantia = 'ativa' | 'vencida' | 'sem_garantia'

export interface UsinaResumo {
  id: string
  nome: string
  id_usina_provedor: string
  provedor: string
  capacidade_kwp: number
  ativo: boolean
  endereco: string
  cidade: string
  telefone: string
  status_garantia: StatusGarantia
  criado_em: string
  atualizado_em: string
}

export interface SnapshotInversorResumo {
  coletado_em: string
  estado: string
  pac_kw: number
  energia_hoje_kwh: number
  energia_total_kwh: number
  tensao_ac_v: number | null
  corrente_ac_a: number | null
  tensao_dc_v: number | null
  corrente_dc_a: number | null
  frequencia_hz: number | null
  temperatura_c: number | null
  strings_mppt: Record<string, unknown>
  soc_bateria: number | null
}

export interface InversorResumo {
  id: string
  numero_serie: string
  modelo: string
  id_inversor_provedor: string
  ultimo_snapshot: SnapshotInversorResumo | null
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
  cidade: string
  telefone: string
  latitude: number | null
  longitude: number | null
  status_garantia: StatusGarantia
  tensao_sobretensao_v: number
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
  tensao_sobretensao_v?: number
}
