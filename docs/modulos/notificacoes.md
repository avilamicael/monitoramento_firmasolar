---
title: Módulo — Notificações
tipo: modulo
tags: [notificacoes, email, whatsapp]
---

# Módulo: Notificações

Envia notificações para operadores quando alertas são criados ou escalonados. Suporta Email e WhatsApp. Configurável em tempo de execução sem restart.

**Arquivos:**
- `notificacoes/models.py`
- `notificacoes/servico.py`
- `notificacoes/base.py`
- `notificacoes/backends/email.py`
- `notificacoes/backends/whatsapp.py`

---

## Model: ConfiguracaoNotificacao

```python
class ConfiguracaoNotificacao:
    canal         : 'email' | 'whatsapp'  (unique)
    ativo         : BooleanField
    destinatarios : TextField (um por linha)
    notificar_critico   : BooleanField
    notificar_importante: BooleanField
    notificar_aviso     : BooleanField
    notificar_info      : BooleanField

    def lista_destinatarios() -> list[str]:
        return [d.strip() for d in destinatarios.split('\n') if d.strip()]
```

A configuração é lida **a cada notificação** do banco, permitindo alterações sem restart dos containers.

---

## Fluxo de Notificação

```python
# Chamado em sincronizar_alertas() quando:
ServicoNotificacao.notificar_novo_alerta(alerta)      # alerta recém criado
ServicoNotificacao.notificar_alerta_escalado(alerta)  # nível aumentou

# Internamente:
para cada ConfiguracaoNotificacao ativo:
    se nivel_do_alerta está habilitado no canal:
        backend = EmailBackend ou WhatsAppBackend
        se backend.is_disponivel():
            backend.enviar(DadosNotificacao, destinatarios)
            # falha em um canal não afeta os demais
```

---

## DadosNotificacao

Estrutura passada para os backends:

```python
@dataclass
class DadosNotificacao:
    id_alerta     : str
    nome_usina    : str
    provedor      : str
    mensagem      : str
    nivel         : str   # 'critico', 'importante', 'aviso', 'info'
    sugestao      : str
    equipamento_sn: str
    inicio        : datetime
    novo          : bool  # True = novo alerta, False = escalonado
```

---

## Backend: Email

**Arquivo:** `notificacoes/backends/email.py`

**Disponível se:** `EMAIL_HOST` está preenchido no `.env`.

**Formato do assunto:**
```
[NOVO ALERTA] 🔴 CRÍTICO — Nome da Usina (fusionsolar)
[ALERTA ESCALADO] 🟠 IMPORTANTE — Nome da Usina (hoymiles)
```

**Corpo do email:**
```
Usina:        Nome da Usina
Nível:        🔴 CRÍTICO
Problema:     Descrição do alarme
Equipamento:  SN-123456 (se disponível)
Sugestão:     Orientação de resolução
Início:       22/03/2026 16:30
```

**Configuração no `.env`:**
```bash
EMAIL_HOST=smtp.gmail.com
EMAIL_PORTA=587
EMAIL_USUARIO=conta@gmail.com
EMAIL_SENHA=app-password
NOTIFICACAO_EMAIL_DE=noreply@firmasolar.com.br
```

---

## Backend: WhatsApp

**Arquivo:** `notificacoes/backends/whatsapp.py`

Suporta dois provedores, selecionável via `WHATSAPP_PROVEDOR` no `.env`:

### Meta Cloud API (padrão: `WHATSAPP_PROVEDOR=meta`)

```
POST https://graph.facebook.com/v19.0/{PHONE_ID}/messages
Authorization: Bearer {WHATSAPP_API_TOKEN}
Body: {
    "messaging_product": "whatsapp",
    "to": "5511999999999",
    "type": "text",
    "text": {"body": "mensagem"}
}
```

**Configuração:**
```bash
WHATSAPP_PROVEDOR=meta
WHATSAPP_API_TOKEN=EAAxxxx...
WHATSAPP_PHONE_ID=123456789
```

### Evolution API (self-hosted: `WHATSAPP_PROVEDOR=evolution`)

```
POST {WHATSAPP_EVOLUTION_URL}/message/sendText/{INSTANCIA}
apikey: {WHATSAPP_EVOLUTION_TOKEN}
Body: {
    "number": "5511999999999",
    "text": "mensagem"
}
```

**Configuração:**
```bash
WHATSAPP_PROVEDOR=evolution
WHATSAPP_EVOLUTION_URL=http://evolution.exemplo.com.br
WHATSAPP_EVOLUTION_TOKEN=seu-token
WHATSAPP_EVOLUTION_INSTANCIA=firma-solar
```

**Formato da mensagem WhatsApp:**
```
🆕 *NOVO ALERTA* 🔴

*Usina:* Nome da Usina
*Provider:* fusionsolar
*Nível:* 🔴 CRÍTICO
*Problema:* Descrição do alarme
*Equipamento:* SN-123456
*Sugestão:* Orientação
*Início:* 22/03/2026 16:30
```

---

## Configurar pelo Admin

1. Acesse `Django Admin > Notificações > Configurações`
2. Crie ou edite a configuração para `email` ou `whatsapp`
3. Marque `ativo = True`
4. Preencha os destinatários (um por linha):
   - Email: endereços de email
   - WhatsApp: números com DDI (`5511999999999`)
5. Selecione quais níveis notificar
6. Salve — efetivo imediatamente, sem restart

---

## Veja Também

- [[modulos/alertas]]
- [[infraestrutura/variaveis-de-ambiente]]
