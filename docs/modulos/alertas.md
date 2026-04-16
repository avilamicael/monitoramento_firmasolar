---
title: Módulo — Alertas
tipo: modulo
tags: [alertas, catalogo, supressao, notificacoes, garantia]
updated: 2026-04-15
---

# Módulo: Alertas

Gerencia o ciclo de vida completo dos alarmes: desde o recebimento da API do provedor (alertas externos) e da análise dos dados coletados (alertas internos) até a notificação do operador, com suporte a catálogo, supressão granular, supressão inteligente (desligamento ao entardecer) e filtro por garantia ativa.

**Arquivos:**
- `alertas/models.py` — `Alerta`, `CatalogoAlarme`, `RegraSupressao`, `SupressaoInterna`
- `alertas/analise.py` — Análise interna (alertas baseados em snapshots)
- `alertas/categorizacao.py` — Inferência automática de categoria
- `alertas/supressao_inteligente.py` — Heurística de desligamento gradual
- `alertas/admin.py` — Admin

---

## Models

### CatalogoAlarme

Registro de cada tipo de alarme conhecido. Criado automaticamente na primeira ocorrência.

```python
class CatalogoAlarme:
    provedor              : CharField (solis/hoymiles/fusionsolar/solarman/auxsol)
    id_alarme_provedor    : CharField
    nome_pt               : CharField
    nome_original         : CharField
    tipo                  : 'equipamento' | 'comunicacao' | 'rede_eletrica' |
                            'sistema_desligado' | 'preventivo'
    nivel_padrao          : 'info' | 'aviso' | 'importante' | 'critico'
    nivel_sobrescrito     : BooleanField
    suprimido             : BooleanField
    sugestao              : TextField
    criado_auto           : BooleanField

    unique_together: (provedor, id_alarme_provedor)
```

### RegraSupressao

Suprime um tipo de alarme (do catálogo) em escopo `usina` ou `todas`, com expiração opcional (`ativo_ate=None` → permanente).

### SupressaoInterna

Suprime um tipo de **alerta interno** (ex: `sem_comunicacao`) para uma usina específica. Usado quando o cliente não quer mais ver aquele alerta. Para reativar, basta deletar o registro.

```python
class SupressaoInterna:
    usina     : FK → Usina
    categoria : CharField  # ex: 'sem_comunicacao'
    motivo    : TextField
    unique_together: (usina, categoria)
```

### Alerta

Ocorrência concreta. Pode vir do provedor ou ser gerada internamente.

```python
class Alerta:
    usina               : FK → Usina
    catalogo_alarme     : FK → CatalogoAlarme (null para alertas internos)
    origem              : 'provedor' | 'interno'
    categoria           : str  # preenchida apenas para alertas internos
    id_alerta_provedor  : CharField  # chave natural
    equipamento_sn      : CharField
    mensagem            : TextField
    nivel               : 'info' | 'aviso' | 'importante' | 'critico'
    estado              : 'ativo' | 'resolvido'
    inicio              : DateTimeField
    fim                 : DateTimeField (null)
    sugestao            : TextField
    anotacoes           : TextField
    notificacao_enviada : BooleanField
    payload_bruto       : JSONField

    unique_together: (usina, id_alerta_provedor)
    indexes: (estado, -inicio), (nivel, estado), (usina, estado),
             (origem, estado), (categoria, estado)
```

> O estado `em_atendimento` foi **removido** — hoje o ciclo de vida é apenas `ativo → resolvido` (e reaberto se o problema volta). Dashboards e queries não devem mais referenciar `em_atendimento`.

Para alertas internos, `id_alerta_provedor` tem a forma `interno_{categoria}_{chave}` (chave é geralmente `id_usina_provedor`) — garante 1 alerta aberto por usina+categoria.

---

## Alertas do provedor — sincronização

Executada por `ServicoIngestao.sincronizar_alertas()` (ver [[modulos/coleta#ServicoIngestao]]).

### Fluxo resumido

1. Para cada alerta retornado pela API:
   - Alertas marcados como `resolvido` pelo próprio provedor são ignorados na criação/atualização (e fechados automaticamente no passo 2 se já existirem).
   - `get_or_create` no `CatalogoAlarme` (auto-inferência de categoria em `alertas/categorizacao.py`).
   - Supressão global (`catalogo.suprimido=True`) → descartar.
   - `RegraSupressao` ativa (`todas` ou `usina`, respeitando `ativo_ate`) → descartar.
   - Nível efetivo: `catalogo.nivel_padrao` se `nivel_sobrescrito=True`, senão o nível vindo da API.
   - Supressão inteligente para `sistema_desligado`: se não há alerta aberto para o mesmo ID e `e_desligamento_gradual(usina)` detecta pôr do sol normal, descarta (ver `supressao_inteligente.py`).
   - `Alerta.objects.get_or_create` por `(usina, id_alerta_provedor)`.
   - Novo → `transaction.on_commit` agenda `enviar_notificacao_alerta.delay(id, 'novo')`.
   - Existente → detecta escalonamento via `nivel_escalou_para(...)`; atualiza mensagem/nível/sugestão; reabre se estava resolvido (limpa `fim`).

2. Alertas `origem='provedor'` que ainda estão `ativo` no banco mas não foram enviados neste ciclo → `estado='resolvido'`, `fim=now()`.

> A auto-resolução só afeta alertas `origem='provedor'`. Alertas internos têm seu próprio ciclo de resolução (ver abaixo).

---

## Alertas internos

Gerados em `alertas/analise.py` → `analisar_usina(usina, snapshot, inversores_snapshots)`, chamada por `coletar_dados_provedor` após salvar snapshots.

### Regra de garantia (ALT-04)

**Alertas internos só são gerados para usinas com garantia ativa.**

```python
def _tem_garantia_ativa(usina) -> bool:
    garantia = getattr(usina, 'garantia', None)
    return garantia is not None and garantia.ativa

def analisar_usina(usina, snapshot, inversores_snapshots):
    if not _tem_garantia_ativa(usina):
        return
    ...
```

Separação clara: coleta acontece para **todas** as usinas (snapshots populam o dashboard), mas **alertamento operacional** é apenas para quem paga — usinas sem garantia ou com garantia expirada continuam populando o banco mas não produzem ruído de alertas. Ver [[arquitetura/decisoes]].

### Categorias de alerta interno

| Categoria | Quando dispara | Nível | Supressão |
|---|---|---|---|
| `garantia_expirando` | Dias restantes ≤ `dias_aviso_garantia_proxima` (default 30) | `aviso`; escala para `importante` se ≤ `dias_aviso_garantia_urgente` (default 7) | auto-resolve se renovar ou perder garantia |
| `tensao_zero` | Tensão AC = 0 em 1+ inversor | `critico` | auto-resolve quando volta |
| `sobretensao` | Tensão AC ≥ `usina.tensao_sobretensao_v` (default 240V) | `aviso` | auto-resolve quando volta |
| `sem_geracao_diurna` | `potencia_kw ≤ 0` em horário comercial (8h–18h) com inversores online | `importante` | auto-resolve quando volta |
| `sem_comunicacao` | `potencia_kw ≤ 0` em horário comercial com **todos** os inversores offline (ou `data_medicao` > 24h atrás) | `aviso` (até 7 dias), `importante` (> 7 dias) | `SupressaoInterna` por usina |
| `corrente_baixa` | Corrente AC ou DC ≤ 0.1A por 2h+ entre 9h e 17h | `critico` | auto-resolve quando volta |

> Os alertas de inversor são **agrupados por usina+categoria** — uma usina com 5 inversores em sobretensão gera 1 alerta, não 5.

### Aviso de garantia (novo)

```python
def _verificar_garantia_expirando(usina):
    garantia = getattr(usina, 'garantia', None)
    if garantia is None or not garantia.ativa:
        _resolver_alerta_interno(usina, 'garantia_expirando', chave)
        return
    config = ConfiguracaoSistema.obter()
    dias = garantia.dias_restantes
    if dias > config.dias_aviso_garantia_proxima:
        _resolver_alerta_interno(usina, 'garantia_expirando', chave)
        return
    nivel = 'importante' if dias <= config.dias_aviso_garantia_urgente else 'aviso'
    _enriquecer_ou_criar(usina, 'garantia_expirando', chave, nivel, mensagem, sugestao)
```

Auto-resolve quando: garantia é renovada (`dias_restantes > dias_aviso_garantia_proxima`) ou a usina perde a garantia (filtro de garantia ativa para todo alerta interno).

### Fluxo de criação/resolução

Funções `_enriquecer_ou_criar` e `_resolver_alerta_interno` usam ID sintético `interno_{categoria}_{id_usina_provedor}`:

- `_enriquecer_ou_criar`: `get_or_create` do Alerta; se já existia resolvido, reabre (`estado='ativo'`, `fim=None`); se o nível subiu, atualiza; respeita `SupressaoInterna`. **Não enriquece mais alertas do provedor** (removido para evitar categorias erradas — ver `1d305bf`).
- `_resolver_alerta_interno`: `update` para `estado='resolvido'`, `fim=now()` (não reabre).

---

## Nível efetivo e categoria efetiva

### Nível efetivo (aplicação em sincronização)

```python
nivel_efetivo = catalogo.nivel_padrao if catalogo.nivel_sobrescrito else nivel_da_api
```

### Categoria efetiva (exibição na API)

`GET /api/alertas/` e `GET /api/alertas/{id}/` retornam `categoria_efetiva`:

- Alertas internos: `Alerta.categoria` (preenchido na criação).
- Alertas do provedor: fallback para `catalogo_alarme.tipo` (pois `Alerta.categoria` fica vazia — o enriquecimento automático foi removido para evitar categorização incorreta).

```python
def _categoria_efetiva(obj):
    if obj.categoria:
        return obj.categoria
    cat = getattr(obj, 'catalogo_alarme', None)
    return cat.tipo if cat and cat.tipo else ''
```

---

## Ordenação por severidade

`AlertaViewSet.get_queryset()` usa `Case/When` no campo `nivel`:

```
critico → 0, importante → 1, aviso → 2, info → 3, default → 4
ORDER BY nivel_ordem, -inicio
```

O usuário sempre vê os alertas mais severos primeiro; a coluna "Data" no frontend também exibe horário junto com data.

---

## Ciclo de vida

```
API reporta ou analisar_usina detecta
        │
        ▼
     [ativo]
        │
        ├── API some / condição desaparece → [resolvido]
        │                                        │
        │                             problema reaparece → [ativo] (reabre, fim=None)
        │
        └── operador marca resolvido (PATCH) → [resolvido]
```

---

## Endpoints de API

| Método | Path | Permissão | Descrição |
|---|---|---|---|
| GET | `/api/alertas/` | autenticado | Lista paginada, filtros em `AlertaFilterSet`, ordenada por severidade |
| GET | `/api/alertas/{id}/` | autenticado | Detalhe com `categoria_efetiva`, `com_garantia`, `usina_nome`, `usina_provedor` |
| PATCH | `/api/alertas/{id}/` | autenticado | Atualiza apenas `estado` e `anotacoes` (restringe mass assignment) |

POST/DELETE bloqueados — alertas são geridos pela coleta (T-2-09). Campos excluídos dos serializers: `payload_bruto` (T-2-07), `notificacao_enviada`.

---

## Admin

**CatalogoAlarme:** filtros por provedor, tipo, nível, suprimido, criado_auto. Permite ajustar nível e adicionar sugestão.

**RegraSupressao:** cria supressões por usina ou globais, com `ativo_ate` para temporárias.

**SupressaoInterna:** suprime alertas internos por usina+categoria.

**Alerta:** listagem com nível colorido, filtros por nível/estado/provedor/origem, `anotacoes` editável.

---

## Veja Também

- [[modulos/notificacoes]]
- [[modulos/coleta]]
- [[modulos/usinas]]
- [[arquitetura/fluxo-de-coleta]]
- [[arquitetura/decisoes]]
- [[ALERTAS]]
