---
title: Módulo — Notificações
tipo: modulo
tags: [notificacoes, email, whatsapp, webhook, painel]
updated: 2026-04-15
---

# Módulo: Notificações

Envia notificações para operadores quando alertas são criados ou escalonados. Suporta três canais (email, WhatsApp, webhook) e também persiste no painel interno (sino do frontend). Configurável em tempo de execução sem restart.

**Arquivos:**
- `notificacoes/models.py` — `Notificacao`, `NotificacaoLeitura`, `ConfiguracaoNotificacao`
- `notificacoes/servico.py` — Despacho
- `notificacoes/tasks.py` — `enviar_notificacao_alerta` (Celery)
- `notificacoes/base.py` — Interface `BackendNotificacao` + `DadosNotificacao`
- `notificacoes/backends/email.py`
- `notificacoes/backends/whatsapp.py`
- `notificacoes/backends/webhook.py` — **Novo canal**

---

## Visão geral do fluxo

```
sincronizar_alertas()  ou  analisar_usina()
          │
          ▼
  transaction.on_commit(
    enviar_notificacao_alerta.delay(id, 'novo'|'escalado')
  )
          │
          ▼ (após commit da coleta)
enviar_notificacao_alerta (Celery task, max_retries=3)
          │
          ├─► _persistir_notificacao_painel(alerta, motivo)   [painel / sino]
          │
          └─► ServicoNotificacao._despachar(alerta)
                  ├─► EmailBackend (se canal ativo e nível habilitado)
                  ├─► WhatsAppBackend
                  └─► WebhookBackend
```

---

## Modelos de notificação do painel

### Notificacao

Notificação persistida exibida no sino do painel de cada usuário autenticado.

```python
class Notificacao:
    id           : UUIDField
    titulo       : CharField
    mensagem     : TextField
    tipo         : 'alerta' | 'sistema' | 'garantia' | 'outro'
    nivel        : 'info' | 'aviso' | 'importante' | 'critico'
    link         : CharField (ex: '/alertas/{uuid}')
    apenas_staff : BooleanField  # True → só is_staff veem
    criado_em    : DateTimeField
```

### NotificacaoLeitura

Estado "lida" é **individual por usuário**. A presença de registro significa lida; a ausência, não lida. `unique_together: (usuario, notificacao)`.

### Hook automático

A task `enviar_notificacao_alerta` chama `_persistir_notificacao_painel(alerta, motivo)` para toda notificação de alerta — cria `Notificacao(tipo='alerta', nivel=<nível do alerta>, link='/alertas/{id}', apenas_staff=False)`. Isso roda **em paralelo** ao envio por email/WhatsApp/webhook; falha em persistir só gera warning.

### Endpoints do painel (`/api/notificacoes/`)

Todos exigem autenticação.

| Método | Path | Descrição |
|---|---|---|
| GET | `/api/notificacoes/` | Lista paginada (20/página). `?apenas_nao_lidas=true` filtra. Notificações com `apenas_staff=True` só aparecem para `is_staff`. |
| GET | `/api/notificacoes/nao-lidas-count/` | Retorna `{count: N}` — usado pelo badge do sino (polling de 60s no frontend). |
| POST | `/api/notificacoes/{id}/marcar-lida/` | Marca uma como lida. |
| POST | `/api/notificacoes/marcar-todas-lidas/` | Bulk-create de `NotificacaoLeitura` para todas as visíveis ainda não lidas. |

No frontend, o componente do sino no header mostra o badge e, ao abrir, lista as últimas notificações. Clique em uma redireciona para `link` e a marca como lida.

---

## Model: ConfiguracaoNotificacao

Configura os canais externos de notificação. Um registro por canal (único).

```python
class ConfiguracaoNotificacao:
    canal         : 'email' | 'whatsapp' | 'webhook'  (unique)
    ativo         : BooleanField
    destinatarios : TextField   # email: endereços; whatsapp: +55...; webhook: URLs HTTP(S)
    notificar_critico    : BooleanField (default True)
    notificar_importante : BooleanField (default True)
    notificar_aviso      : BooleanField (default False)
    notificar_info       : BooleanField (default False)
    atualizado_em : DateTimeField

    def lista_destinatarios() -> list[str]:
        # aceita separador por vírgula OU quebra de linha
```

Leitura **a cada notificação** — sem restart para alterar.

### Endpoints CRUD (`/api/notificacoes-config/`)

Restritos a `is_staff=True` (ModelViewSet completo).

| Método | Path |
|---|---|
| GET | `/api/notificacoes-config/` (lista) |
| GET | `/api/notificacoes-config/{id}/` |
| POST | `/api/notificacoes-config/` |
| PATCH | `/api/notificacoes-config/{id}/` |
| DELETE | `/api/notificacoes-config/{id}/` |

**Frontend:** página `/gestao-notificacoes` com abas para os 3 canais.

---

## Despacho (`ServicoNotificacao`)

```python
# servico.py — seleção do backend
_BACKENDS_MAP = {
    'email':    EmailBackend,
    'whatsapp': WhatsAppBackend,
    'webhook':  WebhookBackend,
}
```

Para cada `ConfiguracaoNotificacao(ativo=True)`:

1. Verifica se o nível do alerta está habilitado no canal (`notificar_{nivel}`).
2. Valida destinatários não vazios.
3. Carrega o backend e chama `is_disponivel()` (valida env vars).
4. Chama `backend.enviar(DadosNotificacao, destinatarios)`.
5. Falha em um canal **não afeta** os demais — erro é logado.

### DadosNotificacao

```python
@dataclass
class DadosNotificacao:
    id_alerta      : str
    nome_usina     : str
    provedor       : str
    mensagem       : str
    nivel          : str  # critico/importante/aviso/info
    sugestao       : str
    equipamento_sn : str
    inicio         : datetime
    novo           : bool  # True = novo, False = escalado
```

---

## Backend: Email

Disponível se `EMAIL_HOST` estiver preenchido. SMTP/TLS.

**Env vars:** `EMAIL_HOST`, `EMAIL_PORTA`, `EMAIL_USUARIO`, `EMAIL_SENHA`, `NOTIFICACAO_EMAIL_DE`.

**Assunto/corpo:** formato como na versão anterior (mantido sem alterações).

---

## Backend: WhatsApp

Suporta Meta Cloud API ou Evolution API (self-hosted), selecionável via `WHATSAPP_PROVEDOR`.

**Env vars comuns:** `WHATSAPP_PROVEDOR` (default `meta`).

**Meta:** `WHATSAPP_API_TOKEN`, `WHATSAPP_PHONE_ID`.
**Evolution:** `WHATSAPP_EVOLUTION_URL`, `WHATSAPP_EVOLUTION_TOKEN`, `WHATSAPP_EVOLUTION_INSTANCIA`.

---

## Backend: Webhook (novo)

Para cada URL nos destinatários, faz `POST JSON` com o payload abaixo. Não exige credenciais — `is_disponivel()` retorna sempre `True`. Destinatários inválidos (não começam com `http(s)://`) são ignorados com warning. Timeout de 10s por URL.

**Payload:**

```json
{
  "id_alerta": "uuid",
  "nome_usina": "Nome",
  "provedor": "fusionsolar",
  "mensagem": "...",
  "nivel": "critico",
  "sugestao": "...",
  "equipamento_sn": "...",
  "inicio": "2026-04-15T16:30:00+00:00",
  "motivo": "novo"
}
```

Integração simples com Slack (Incoming Webhook), Discord, Zapier, n8n, etc.

---

## Celery Task

```python
@shared_task(bind=True, max_retries=3, default_retry_delay=60, ignore_result=True)
def enviar_notificacao_alerta(self, alerta_id, motivo):
    ...
    _persistir_notificacao_painel(alerta, motivo)
    ServicoNotificacao().notificar_novo_alerta(alerta) | notificar_alerta_escalado(alerta)
```

Agendada via `transaction.on_commit` — só executa após a transação de coleta fechar. Falha no envio gera retry automático (max 3, 60s entre tentativas); falha definitiva **não afeta** a coleta.

---

## Veja Também

- [[modulos/alertas]]
- [[modulos/coleta]]
- [[infraestrutura/variaveis-de-ambiente]]
- [[Frontend - Painel Administrativo]]
