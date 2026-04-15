export type TipoNotificacao = 'alerta' | 'sistema' | 'garantia' | 'outro'
export type NivelNotificacao = 'info' | 'aviso' | 'importante' | 'critico'

export interface Notificacao {
  id: string
  titulo: string
  mensagem: string
  tipo: TipoNotificacao
  nivel: NivelNotificacao
  link: string
  apenas_staff: boolean
  criado_em: string
  lida: boolean
}

export interface PaginatedNotificacoes {
  count: number
  next: string | null
  previous: string | null
  results: Notificacao[]
}
