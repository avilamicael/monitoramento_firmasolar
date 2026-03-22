"""
Data migration: pré-popula o catálogo com os alarmes documentados da API FusionSolar.

Fonte: FusionSolar thirdData API — 9.1.10 Common Inverter Alarms
"""
from django.db import migrations

# (id_alarme_provedor, nome_pt, nome_original, tipo, nivel_padrao, sugestao)
_ALARMES_FUSIONSOLAR = [
    (
        '2001',
        'Sobretensão da string',
        'String Voltage High',
        'string_pv',
        'importante',
        'Verifique se há módulos em excesso na string. A tensão de circuito aberto não deve ultrapassar a tensão máxima de operação do inversor.',
    ),
    (
        '2002',
        'Arco elétrico CC (AFCI)',
        'DC Arc Fault (AFCI)',
        'segurança',
        'critico',
        'Inspecione os cabos CC e conexões em busca de danos ou pontos de arco. Risco de incêndio — não reative sem inspeção técnica.',
    ),
    (
        '2003',
        'Arco elétrico CC (AFCI)',
        'DC Arc Fault (AFCI)',
        'segurança',
        'critico',
        'Inspecione os cabos CC e conexões em busca de danos ou pontos de arco. Risco de incêndio — não reative sem inspeção técnica.',
    ),
    (
        '2009',
        'Curto-circuito da string ao terra',
        'String Short-Circuited to Ground',
        'segurança',
        'critico',
        'Verifique o isolamento dos cabos CC. Risco de choque elétrico — desconecte o sistema antes da inspeção.',
    ),
    (
        '2010',
        'Entrada CC anormal',
        'Abnormal DC Input',
        'string_pv',
        'aviso',
        'Verifique as conexões das strings e a tensão de entrada CC.',
    ),
    (
        '2011',
        'Conexão reversa de string',
        'String Reverse Connection',
        'string_pv',
        'importante',
        'A polaridade de uma ou mais strings está invertida. Corrija as conexões antes de ligar o sistema.',
    ),
    (
        '2012',
        'Retrocorrente de string',
        'String Current Backfeed',
        'string_pv',
        'importante',
        'Verifique se há diferença de potência entre strings paralelas. Pode indicar sombreamento severo ou módulo defeituoso.',
    ),
    (
        '2014',
        'Alta tensão de string ao terra',
        'High String Voltage to Ground',
        'string_pv',
        'importante',
        'Verifique o isolamento dos módulos e cabos. Possível acúmulo de sujeira condutiva ou dano de isolação.',
    ),
    (
        '2015',
        'Perda de string fotovoltaica',
        'PV String Loss',
        'string_pv',
        'importante',
        'Uma ou mais strings deixaram de produzir. Verifique fusíveis de string, conexões e módulos.',
    ),
    (
        '2021',
        'Falha de autoverificação AFCI',
        'AFCI Self-Check Failure',
        'segurança',
        'importante',
        'O sistema de detecção de arco (AFCI) falhou na autoverificação. Contate o suporte técnico Huawei.',
    ),
    (
        '2031',
        'Fase em curto com terra de proteção (PE)',
        'Phase wire short-circuited to PE',
        'segurança',
        'critico',
        'Risco elétrico grave. Desconecte imediatamente e contate técnico qualificado antes de qualquer inspeção.',
    ),
    (
        '2032',
        'Falha na rede elétrica',
        'Grid Failure',
        'rede_eletrica',
        'critico',
        'Verifique se a concessionária está fornecendo energia. Se a rede estiver normal, verifique as conexões CA do inversor.',
    ),
    (
        '2033',
        'Subtensão de rede',
        'Grid Undervoltage',
        'rede_eletrica',
        'importante',
        'A tensão da rede está abaixo do limite mínimo. Informe a concessionária se o problema persistir.',
    ),
    (
        '2034',
        'Sobretensão de rede',
        'Grid Overvoltage',
        'rede_eletrica',
        'importante',
        'A tensão da rede está acima do limite máximo. Informe a concessionária se o problema persistir.',
    ),
    (
        '2039',
        'Sobrecorrente CA',
        'AC Overcurrent',
        'rede_eletrica',
        'critico',
        'Verifique se há curto-circuito no lado CA. Inspecione as conexões de saída do inversor.',
    ),
    (
        '2040',
        'Componente CC elevado',
        'DC Component Overhigh',
        'rede_eletrica',
        'importante',
        'A componente CC na saída CA está acima do limite. Contate suporte técnico para diagnóstico.',
    ),
    (
        '2051',
        'Corrente residual anormal',
        'Abnormal Residual Current',
        'segurança',
        'critico',
        'Pode indicar falha de isolação. Inspecione os módulos e cabeamento antes de reativar o sistema.',
    ),
    (
        '2061',
        'Aterramento anormal',
        'Abnormal Grounding',
        'aterramento',
        'importante',
        'Verifique as conexões de aterramento do sistema. O condutor de proteção (PE) deve estar íntegro.',
    ),
    (
        '2062',
        'Baixa resistência de isolação',
        'Low Insulation Resistance',
        'segurança',
        'critico',
        'Risco de choque elétrico. Localize e corrija o defeito de isolação nos módulos ou cabos antes de religar.',
    ),
    (
        '2064',
        'Falha no dispositivo',
        'Device Fault',
        'hardware',
        'critico',
        'Falha interna no inversor. Registre o código de evento e contate o suporte Huawei.',
    ),
    (
        '2066',
        'Licença expirada',
        'License Expired',
        'licenca',
        'info',
        'Renove a licença do inversor pelo portal FusionSolar ou contate o distribuidor Huawei.',
    ),
    (
        '2067',
        'Coletor de energia com falha',
        'Faulty power collector',
        'hardware',
        'aviso',
        'Verifique o coletor de potência (power collector). Substitua se necessário.',
    ),
    (
        '2075',
        'Curto-circuito em porta periférica',
        'Peripheral Port Short Circuit',
        'hardware',
        'aviso',
        'Desconecte os dispositivos conectados às portas periféricas (RS485, USB) e verifique o cabo.',
    ),
    (
        '2080',
        'Configuração anormal de módulo fotovoltaico',
        'Abnormal PV Module Configuration',
        'configuracao',
        'aviso',
        'Verifique o número de módulos por string e os parâmetros configurados no inversor.',
    ),
    (
        '2082',
        'Caixa de backup anormal',
        'Backup Box abnormal',
        'hardware',
        'aviso',
        'Verifique a caixa de backup (backup box) e suas conexões.',
    ),
    (
        '2086',
        'Anormalidade no ventilador externo',
        'External Fan Abnormality',
        'hardware',
        'aviso',
        'Verifique o ventilador externo do inversor. Limpe ou substitua se obstruído ou defeituoso.',
    ),
    (
        '2088',
        'Unidade de proteção CC anormal',
        'Abnormal DC protection unit',
        'hardware',
        'importante',
        'Verifique a unidade de proteção CC do inversor. Contate suporte técnico se o problema persistir.',
    ),
    (
        '2103',
        'Temperatura anormal no terminal CA',
        'AC Terminal Temperature Abnormal',
        'hardware',
        'importante',
        'Verifique as conexões dos terminais CA e se a ventilação do inversor está adequada.',
    ),
    (
        '2104',
        'Temperatura anormal no terminal CC',
        'DC Terminal Temperature Abnormal',
        'hardware',
        'importante',
        'Verifique as conexões dos terminais CC e se a ventilação do inversor está adequada.',
    ),
]


def _popular_catalogo(apps, schema_editor):
    CatalogoAlarme = apps.get_model('alertas', 'CatalogoAlarme')
    for (id_alarme, nome_pt, nome_original, tipo, nivel, sugestao) in _ALARMES_FUSIONSOLAR:
        CatalogoAlarme.objects.get_or_create(
            provedor='fusionsolar',
            id_alarme_provedor=id_alarme,
            defaults={
                'nome_pt': nome_pt,
                'nome_original': nome_original,
                'tipo': tipo,
                'nivel_padrao': nivel,
                'sugestao': sugestao,
                'criado_auto': False,
            },
        )


def _remover_catalogo(apps, schema_editor):
    CatalogoAlarme = apps.get_model('alertas', 'CatalogoAlarme')
    ids = [row[0] for row in _ALARMES_FUSIONSOLAR]
    CatalogoAlarme.objects.filter(
        provedor='fusionsolar',
        id_alarme_provedor__in=ids,
        criado_auto=False,
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('alertas', '0002_catalogo_supressao'),
    ]

    operations = [
        migrations.RunPython(_popular_catalogo, _remover_catalogo),
    ]
