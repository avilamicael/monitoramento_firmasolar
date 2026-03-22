---
title: Módulo — Alertas
tipo: modulo
tags: [alertas, catalogo, supressao, notificacoes]
---

# Módulo: Alertas

Gerencia o ciclo de vida completo dos alarmes: desde o recebimento da API do provedor até a notificação do operador, com suporte a catálogo, supressão granular e histórico de ocorrências.

**Arquivos:**
- `alertas/models.py`
- `alertas/admin.py`

---

## Models

### CatalogoAlarme

Registro de cada tipo de alarme conhecido, com metadados e configurações de comportamento.

```python
class CatalogoAlarme:
    provedor              : CharField (solis/hoymiles/fusionsolar)
    id_alarme_provedor    : CharField (ID do tipo no sistema do fabricante)
    nome_pt               : CharField (nome em português)
    nome_original         : CharField (nome como vem da API)
    tipo                  : CharField (ex: 'inversor', 'comunicacao', 'rede')
    nivel_padrao          : 'info' | 'aviso' | 'importante' | 'critico'
    nivel_sobrescrito     : BooleanField (operador ajustou o nível)
    suprimido             : BooleanField (jamais gera alertas, globalmente)
    sugestao              : TextField (orientação de resolução)
    criado_auto           : BooleanField (True = criado durante coleta)

    unique_together: (provedor, id_alarme_provedor)
```

Quando um tipo de alarme desconhecido chega da API, o sistema **cria automaticamente** uma entrada no catálogo com `criado_auto=True` e `nivel_padrao='aviso'`. O operador pode depois ajustar o nível ou suprimir via admin.

### RegraSupressao

Suprime um tipo de alarme em um escopo específico, com expiração opcional.

```python
class RegraSupressao:
    catalogo : FK → CatalogoAlarme
    escopo   : 'usina' | 'todas'
    usina    : FK → Usina (obrigatório se escopo='usina', null se 'todas')
    motivo   : TextField
    ativo_ate: DateTimeField (null = permanente)

    def esta_ativa() -> bool:
        return ativo_ate is None or ativo_ate > now()
```

### Alerta

Ocorrência de um alarme em uma usina específica.

```python
class Alerta:
    usina               : FK → Usina
    catalogo_alarme     : FK → CatalogoAlarme (pode ser null se tipo desconhecido)
    id_alerta_provedor  : CharField (chave natural do provedor)
    equipamento_sn      : CharField (serial do equipamento afetado)
    mensagem            : TextField
    nivel               : 'info' | 'aviso' | 'importante' | 'critico'
    estado              : 'ativo' | 'em_atendimento' | 'resolvido'
    inicio              : DateTimeField
    fim                 : DateTimeField (null se ainda aberto)
    sugestao            : TextField
    anotacoes           : TextField (equipe técnica)
    notificacao_enviada : BooleanField
    payload_bruto       : JSONField

    unique_together: (usina, id_alerta_provedor)
    indexes: (estado, -inicio), (nivel, estado), (usina, estado)
```

---

## Sincronização de Alertas

Executada por `ServicoIngestao.sincronizar_alertas()` ao final de cada coleta, dentro da mesma transação atômica.

### Fluxo

```
Para cada alerta da API:
    1. Busca ou cria CatalogoAlarme (auto)
    2. Verifica supressão:
       - catalogo.suprimido = True?         → ignora
       - RegraSupressao 'todas' ativa?       → ignora
       - RegraSupressao 'usina' ativa?       → ignora
    3. Busca Alerta existente por (usina, id_alerta_provedor)
    4. Se não existe → cria + notifica (novo)
    5. Se existe:
       - Nível escalou? → notifica (escalado)
       - Estava 'resolvido'? → estado = 'ativo' (voltou)
       - Estava 'em_atendimento'? → mantém estado (equipe ciente)
       - Atualiza mensagem, nível, sugestão

Para cada Alerta 'ativo' ou 'em_atendimento' do banco:
    Se não está mais na lista da API:
        estado = 'resolvido'
        fim = now()
```

---

## Estados do Alerta

```
   API reporta
        │
        ▼
     [ativo]
        │
        ├── operador assume → [em_atendimento]
        │                          │
        │                     API some → [resolvido]
        │
        └── API some → [resolvido]
                           │
                      API reporta de novo → [ativo] (novo ciclo)
```

---

## Nível Efetivo

O nível exibido e usado para notificação é determinado assim:

```python
if catalogo_alarme and catalogo_alarme.nivel_sobrescrito:
    nivel = catalogo_alarme.nivel_padrao  # operador ajustou
else:
    nivel = nivel_da_api  # nível original do provedor
```

Isso permite que o operador reclassifique alarmes ruidosos (ex: rebaixar de "importante" para "info") sem depender do fabricante.

---

## Admin

O admin de alertas é a principal interface de operação:

**CatalogoAlarme:**
- Filtros: provedor, tipo, nível, suprimido, criado_auto
- Permite ajustar nível e adicionar sugestão de resolução
- Permite suprimir globalmente um tipo ruidoso

**RegraSupressao:**
- Cria supressões por usina específica ou para todas
- Campo `ativo_ate` para supressões temporárias (ex: durante manutenção)
- Exibe `esta_ativa()` na listagem

**Alerta:**
- Listagem com nível colorido, estado, usina, tempo de abertura
- Campo `anotacoes` para a equipe registrar progresso
- Filtros: nível, estado, provedor
- Readonly: `notificacao_enviada`, `payload_bruto`

---

## Veja Também

- [[modulos/notificacoes]]
- [[arquitetura/fluxo-de-coleta#Sincronização de Alertas]]
- [[arquitetura/decisoes#ADR-009]]
