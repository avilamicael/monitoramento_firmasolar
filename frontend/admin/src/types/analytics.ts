export interface ProvedorPotencia {
  provedor: string
  energia_hoje_kwh: number
  capacidade_kwp: number
  kwh_por_kwp: number
  usinas_ativas: number
}

export interface PotenciaResponse {
  energia_hoje_geral_kwh: number
  kwh_por_kwp_geral: number
  por_provedor: ProvedorPotencia[]
}

export interface ProvedorRanking {
  provedor: string
  inversores_ativos: number
}

export interface RankingResponse {
  ranking: ProvedorRanking[]
}

export interface MapaUsina {
  id: string
  nome: string
  provedor: string
  latitude: number | null
  longitude: number | null
  ativo: boolean
  status: 'sem_dados' | 'normal' | 'aviso' | 'offline' | 'construcao'
}

export interface EnergiaResumo {
  energia_hoje_kwh: number
  energia_mes_kwh: number
  energia_total_kwh: number
  usinas_ativas: number
}

export interface AlertasResumo {
  critico: number
  importante: number
  aviso: number
  info: number
  total_ativos: number
  em_atendimento: number
}

export interface GeracaoDiariaItem {
  dia: string
  energia_kwh: number
  usinas_coletadas: number
}

export interface GeracaoDiaria {
  dias: number
  geracao: GeracaoDiariaItem[]
}
