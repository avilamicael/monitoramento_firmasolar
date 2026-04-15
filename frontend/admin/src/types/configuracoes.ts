export interface ConfiguracaoSistema {
  dias_sem_comunicacao_pausar: number
  meses_garantia_padrao: number
  dias_aviso_garantia_proxima: number
  dias_aviso_garantia_urgente: number
  atualizado_em: string
}

export type ConfiguracaoSistemaUpdate = Omit<ConfiguracaoSistema, 'atualizado_em'>
