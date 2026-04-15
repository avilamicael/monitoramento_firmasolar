export type CanalNotificacao = 'email' | 'whatsapp' | 'webhook'

export interface ConfiguracaoNotificacao {
  id: number
  canal: CanalNotificacao
  ativo: boolean
  destinatarios: string
  destinatarios_lista: string[]
  notificar_critico: boolean
  notificar_importante: boolean
  notificar_aviso: boolean
  notificar_info: boolean
  atualizado_em: string
}

export interface ConfiguracaoNotificacaoPayload {
  canal?: CanalNotificacao
  ativo?: boolean
  destinatarios?: string
  notificar_critico?: boolean
  notificar_importante?: boolean
  notificar_aviso?: boolean
  notificar_info?: boolean
}
