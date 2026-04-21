"""
Catálogo de códigos de falha da linha Q (microinversores) da FoxESS.

Fonte: Manual oficial "Single-Phase Microinverter User Manual" V1.0.0
(https://www.fox-ess.com/Public/Uploads/uploadfile/files/20260105/ENQManualV1.0.0.pdf)
Seção 6.1 — Troubleshooting List.

A OpenAPI da FoxESS não expõe esse catálogo. Os códigos vêm no campo
`currentFault` do `/op/v1/device/real/query` como ID numérico (ex: "4151")
ou lista separada por vírgulas quando múltiplas falhas coexistem
(ex: "4151,4156,4158" — rede caiu e derrubou AC, frequência e tensão).

Cobre os modelos Q1-1600-E, Q1-2000-E, Q1-2400-E. Para novos modelos
(linhas H/T/R de string inverters) os códigos são outros e precisam de
catálogo próprio se forem adicionados à frota.

Níveis usados aqui seguem o contrato de DadosAlerta:
  'critico'    — hardware provavelmente danificado, não se auto-recupera
  'importante' — condição relevante que merece investigação, mas pode normalizar
  'aviso'      — falha transitória que o inversor normalmente resolve sozinho
"""

# Código → (descrição humana, nível, categoria para alertas/categorizacao.py)
CATALOGO_Q: dict[str, tuple[str, str, str]] = {
    # ── PV1..PV4 ─ cada canal tem 4 códigos (short, low V, over V, over I) ───
    '4029': ('PV1 curto-circuito interno',  'critico',    'equipamento'),
    '4030': ('PV1 tensão de entrada baixa', 'aviso',      'equipamento'),
    '4031': ('PV1 sobretensão',             'aviso',      'equipamento'),
    '4032': ('PV1 sobrecorrente',           'aviso',      'equipamento'),

    '4061': ('PV2 curto-circuito interno',  'critico',    'equipamento'),
    '4062': ('PV2 tensão de entrada baixa', 'aviso',      'equipamento'),
    '4063': ('PV2 sobretensão',             'aviso',      'equipamento'),
    '4064': ('PV2 sobrecorrente',           'aviso',      'equipamento'),

    '4093': ('PV3 curto-circuito interno',  'critico',    'equipamento'),
    '4094': ('PV3 tensão de entrada baixa', 'aviso',      'equipamento'),
    '4095': ('PV3 sobretensão',             'aviso',      'equipamento'),
    '4096': ('PV3 sobrecorrente',           'aviso',      'equipamento'),

    '4125': ('PV4 curto-circuito interno',  'critico',    'equipamento'),
    '4126': ('PV4 tensão de entrada baixa', 'aviso',      'equipamento'),
    '4127': ('PV4 sobretensão',             'aviso',      'equipamento'),
    '4128': ('PV4 sobrecorrente',           'aviso',      'equipamento'),

    # ── Falhas AC / rede ────────────────────────────────────────────────────
    '4147': ('Ponte do inversor assimétrica',     'critico',    'equipamento'),
    '4148': ('Tensão desigual nos polos do relé', 'critico',    'equipamento'),
    '4149': ('Ride-through de alta/baixa tensão', 'aviso',      'rede_eletrica'),
    '4150': ('Desligamento remoto',               'importante', 'sistema_desligado'),
    '4151': ('Perda de AC (rede ausente)',        'aviso',      'rede_eletrica'),
    '4152': ('Sobretensão do barramento BUS',     'importante', 'rede_eletrica'),
    '4153': ('Falha de aterramento (GFDI)',       'critico',    'equipamento'),
    '4154': ('Temperatura AC baixa',              'aviso',      'equipamento'),
    '4155': ('Temperatura AC alta',               'importante', 'equipamento'),
    '4156': ('Frequência AC abaixo do limite',    'aviso',      'rede_eletrica'),
    '4157': ('Frequência AC acima do limite',     'aviso',      'rede_eletrica'),
    '4158': ('Tensão AC abaixo do limite',        'aviso',      'rede_eletrica'),
    '4159': ('Sobretensão AC',                    'importante', 'rede_eletrica'),
    '4160': ('Sobrecorrente AC',                  'importante', 'equipamento'),
}

# Severidade → número para comparação (maior = mais severo)
_PESO_NIVEL = {'info': 0, 'aviso': 1, 'importante': 2, 'critico': 3}


def interpretar(codigo_raw: str) -> tuple[str, str, str]:
    """
    Interpreta o campo `currentFault` da FoxESS.

    `codigo_raw` pode ser:
      - "" ou None → retorna fallback genérico
      - "4151" → código único
      - "4151,4156,4158" → múltiplos códigos (rede caiu e gerou 3 falhas ao mesmo tempo)

    Retorna uma tupla (mensagem, nivel, categoria):
      - mensagem: descrições humanas concatenadas por " + "
      - nivel: o mais severo entre os códigos encontrados
      - categoria: a mais severa entre os códigos encontrados (mesma lógica)

    Códigos desconhecidos não quebram — viram "Código X (não catalogado)"
    com nível 'aviso' e categoria 'preventivo'.
    """
    if not codigo_raw:
        return ('Falha reportada pelo inversor', 'critico', 'equipamento')

    codigos = [c.strip() for c in str(codigo_raw).split(',') if c.strip()]
    if not codigos:
        return ('Falha reportada pelo inversor', 'critico', 'equipamento')

    descricoes: list[str] = []
    peso_max = -1
    nivel_max = 'aviso'
    categoria_max = 'preventivo'

    for codigo in codigos:
        if codigo in CATALOGO_Q:
            desc, nivel, categoria = CATALOGO_Q[codigo]
            descricoes.append(f'{desc} (cód. {codigo})')
        else:
            desc = f'Código {codigo} (não catalogado)'
            nivel = 'aviso'
            categoria = 'preventivo'
            descricoes.append(desc)

        peso = _PESO_NIVEL.get(nivel, 0)
        if peso > peso_max:
            peso_max = peso
            nivel_max = nivel
            categoria_max = categoria

    return (' + '.join(descricoes), nivel_max, categoria_max)
