export interface ProvedorPotencia {
  provedor: string
  media_kw: number | null
  usinas_ativas: number
}

export interface PotenciaResponse {
  media_geral_kw: number | null
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
