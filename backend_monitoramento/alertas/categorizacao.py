"""
Inferência automática de categoria para entradas do CatalogoAlarme.

A categoria (campo `tipo`) é preenchida automaticamente quando um tipo de alarme
é encontrado pela primeira vez. O operador pode sobrescrever via admin.

Categorias disponíveis:
  equipamento      — Falha em hardware (inversor, string, módulo)
  comunicacao      — Perda de comunicação / conectividade
  rede_eletrica    — Instabilidade na rede elétrica (grid)
  sistema_desligado — Usina completamente parada / desligada
  preventivo       — Informativo, manutenção, sem urgência operacional
"""

# Mapeamento direto para flags do Hoymiles (determinístico, sem heurística)
_CATEGORIA_POR_FLAG_HOYMILES: dict[str, str] = {
    'g_warn':    'rede_eletrica',
    'l3_warn':   'rede_eletrica',
    's_ustable': 'rede_eletrica',
    's_uoff':    'sistema_desligado',
    'dl':        'comunicacao',
    's_uid':     'comunicacao',
}

# Palavras-chave por categoria — avaliadas em ordem de prioridade
# Mais específico primeiro para evitar colisão
_PALAVRAS_CHAVE_ORDENADAS: list[tuple[str, list[str]]] = [
    ('sistema_desligado', [
        'desligado', 'shutdown', 'parado', 'stopped', 's_uoff',
    ]),
    ('comunicacao', [
        'comunicação', 'comunicacao', 'communication', 'desconex',
        'disconnect', 'datalogger', 'link', 'offline', 'connect',
        'network', 's_uid',
    ]),
    ('rede_eletrica', [
        'grid', 'tensão', 'tensao', 'voltage', 'frequency',
        'frequência', 'frequencia', 'isolamento', 'isolation',
        'rede elétrica', 'rede eletrica', 'l3_warn', 'g_warn',
        's_ustable',
    ]),
    ('equipamento', [
        'inversor', 'inverter', 'string', 'módulo', 'modulo',
        'module', 'device', 'falha', 'failure', 'erro', 'error',
        'temperatura', 'temperature', 'overtemperature',
        'dispositivo', 'hardware', 'pv',
    ]),
]


def inferir_categoria(mensagem: str, provedor: str, id_tipo: str = '') -> str:
    """
    Retorna a categoria mais provável para um tipo de alarme.

    Para Hoymiles, usa o mapeamento direto de flags (determinístico).
    Para os demais provedores, aplica matching por palavras-chave na mensagem.
    Retorna 'preventivo' como fallback quando nenhuma categoria é identificada.

    Args:
        mensagem: texto descritivo do alarme (nome original do provedor)
        provedor: 'solis', 'hoymiles' ou 'fusionsolar'
        id_tipo:  id do tipo no provedor (para Hoymiles é o nome do flag)
    """
    if provedor == 'hoymiles' and id_tipo in _CATEGORIA_POR_FLAG_HOYMILES:
        return _CATEGORIA_POR_FLAG_HOYMILES[id_tipo]

    texto = mensagem.lower()
    for categoria, palavras in _PALAVRAS_CHAVE_ORDENADAS:
        if any(p in texto for p in palavras):
            return categoria

    return 'preventivo'
