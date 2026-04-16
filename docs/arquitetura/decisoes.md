---
title: Decisões de Arquitetura
tipo: decisoes
tags: [decisoes, arquitetura, adr]
updated: 2026-04-15
---

# Decisões de Arquitetura

Registro de decisões técnicas não triviais tomadas no projeto. Formato: contexto → opções → decisão → motivo.

Decisões adicionadas a partir de 2026-04-15 espelham o `DECISIONS.md` da raiz do repositório.

---

## ADR-001 — Monorepo com backend e frontend separados

**Contexto:** O sistema tem dois componentes com ciclos de vida diferentes: o backend Django (coleta e dados) e o Grafana (visualização).

**Opções:**
- Repositório único (monorepo)
- Dois repositórios separados

**Decisão:** Monorepo com pastas `backend_monitoramento/`, `frontend/admin/` (SPA) e `frontend/grafana/` (dashboards).

**Motivo:** A equipe é pequena, os componentes são codependentes (Grafana lê o mesmo banco que o Django escreve) e o deploy é feito na mesma VPS. Um monorepo simplifica o versionamento e a referência cruzada entre componentes.

---

## ADR-002 — Grafana como camada de visualização operacional

**Contexto:** Precisávamos de dashboards operacionais para monitoramento técnico.

**Decisão:** Grafana 10.4 com datasource PostgreSQL direto (rede Docker compartilhada `firmasolar_obs`). Para o painel do cliente/operador, existe uma SPA React/Vite/shadcn separada (ver [[Frontend - Painel Administrativo]]).

**Motivo:** Grafana entrega 95% do valor com 5% do esforço para dashboards técnicos; a SPA React cobre fluxos de operação (alertas, usinas, gestão de provedores, notificações, garantias) que não encaixam bem em Grafana.

---

## ADR-003 — Criptografia Fernet para credenciais no banco

**Decisão:** Fernet (`cryptography`) com chave no `.env` (`CHAVE_CRIPTOGRAFIA`). Protege credenciais de provedores e tokens de sessão no `CacheTokenProvedor`.

**Risco:** Se a chave for perdida, credenciais se tornam ilegíveis — backup é obrigatório.

---

## ADR-004 — Snapshots append-only com janela de 10 minutos

**Decisão:** Snapshots no PostgreSQL com `coletado_em` arredondado para janelas de 10 min. `get_or_create` garante idempotência em retries. Limpeza diária remove dados com > 90 dias.

---

## ADR-005 — Rate limiting distribuído via Redis

**Decisão:** Redis com contador por janela deslizante. Operações atômicas garantem consistência entre workers sem locks de banco.

---

## ADR-006 — FusionSolar: intervalo mínimo de 900 segundos

**Decisão:** `min_intervalo_coleta_segundos=900` (15 min) com usuário dedicado `api_firmasolar`. Se o rate limit voltar, aumentar para 1800s.

> Com a adoção do Beat a cada 30 min em ADR-011, a coleta do FusionSolar fica naturalmente espaçada — o `min_intervalo` continua protegendo contra eventuais forcar-coleta manuais.

---

## ADR-007 — WhiteNoise para arquivos estáticos

**Decisão:** WhiteNoise com `CompressedManifestStaticFilesStorage`. Zero-config, compressão gzip/brotli, cache busting.

---

## ADR-008 — Django Admin + SPA React coexistindo

**Contexto:** Originalmente o Django Admin era a única interface. Com o crescimento do produto e a necessidade de fluxos com mais UX (gestão de provedores, notificações, garantias, configurações), foi criada a SPA React.

**Decisão:** Django Admin continua disponível via SSH tunnel (configurações de baixo nível, catálogo de alarmes, supressões), e a SPA React em `frontend/admin/` atende as operações do dia a dia via API REST (DRF + SimpleJWT).

---

## ADR-009 — Alertas com catálogo e supressão granular

**Decisão:** Três camadas:
1. `CatalogoAlarme` — define nível padrão e permite sobrescrever por operador (`nivel_sobrescrito`).
2. `RegraSupressao` — suprime globalmente ou por usina, com expiração opcional.
3. `Alerta` — ocorrência vinculada ao catálogo (ou a `origem='interno'`).

Complementada pela **supressão inteligente** (`supressao_inteligente.py`) para `sistema_desligado` durante pôr do sol normal.

---

## ADR-010 — Notificações sem restart (canal + painel)

**Decisão:** `ConfiguracaoNotificacao` no banco (3 canais: email, WhatsApp, webhook) + modelos `Notificacao` e `NotificacaoLeitura` para o painel interno. Configurável em tempo de execução sem redeploy. Ver [[modulos/notificacoes]].

---

## ADR-011 — Alertas internos restritos a usinas com garantia ativa

**Data:** 2026-04-15.

**Contexto:** Em produção, o sistema monitora 131 usinas, incluindo várias sem comunicação há 15–580 dias. Isso gerava alertas ruidosos de "sem comunicação" e "sem geração" para usinas que o cliente final abandonou ou nunca contratou serviço de monitoramento.

**Opções consideradas**
- (A) Filtrar na coleta — não coletar usinas sem garantia. **Perde histórico** se a garantia for renovada.
- (B) Filtrar apenas na geração de alertas internos — continua coletando, dashboard tem os dados, alertas só para quem paga.
- (C) Flag explícita por usina, independente de garantia.

**Decisão:** Opção **B**. `alertas/analise.py:_tem_garantia_ativa()` é o gatekeeper — usinas sem garantia ou com garantia expirada continuam populando `SnapshotUsina` e `SnapshotInversor`, mas não produzem `Alerta` interno.

**Por quê:** Separa **coleta de dados** (todas) de **alertamento operacional** (apenas garantia ativa). Permite dashboard "com garantia vs sem garantia" sem nova migração.

---

## ADR-012 — Auto-criação de garantia de 12 meses na primeira coleta

**Data:** 2026-04-15.

**Decisão:** `ServicoIngestao.upsert_usina()` cria `GarantiaUsina(data_inicio=hoje, meses=config.meses_garantia_padrao)` quando a `Usina` é criada pela primeira vez. `get_or_create` é idempotente — não sobrescreve garantia pré-existente.

**Por quê:**
- A coleta é o único ponto onde usinas nascem no sistema — hook ali garante cobertura 100%.
- `data_inicio = hoje` é a interpretação correta: 12 meses a partir de quando **começamos a monitorar**.
- `meses_garantia_padrao` configurável evita hardcode de regra de negócio.

---

## ADR-013 — Auto-pausa de usinas sem comunicação

**Data:** 2026-04-15.

**Contexto:** Usinas que param de comunicar (Wi-Fi caído, datalogger desligado) continuavam gerando tentativas de coleta, ruído de alertas e consumo de quota de API dos provedores.

**Decisão:** Antes de cada ciclo, `_pausar_usinas_inativas()` marca `ativo=False` em toda usina cujo `ultimo_snapshot.coletado_em` seja mais antigo que `ConfiguracaoSistema.dias_sem_comunicacao_pausar` (default 60 dias). No loop principal, usinas com `ativo=False` são puladas.

**Por quê:**
- Reativação é **manual** — usuário decide caso a caso (evita ping-pong automático). Hoje isso pode ser feito pelo frontend (`AtivoToggleButton`) ou pelo admin.
- Valor **configurável** — operador ajusta conforme a realidade da carteira.
- Checagem por ciclo (não job separado) — sem infra adicional.

---

## ADR-014 — Alerta de garantia próxima do fim

**Data:** 2026-04-15.

**Decisão:** Alerta interno `garantia_expirando`, gerado por `_verificar_garantia_expirando()` a cada ciclo de coleta. Dois patamares configuráveis em `ConfiguracaoSistema`:

- `dias_aviso_garantia_proxima` (default 30) — nível "aviso"
- `dias_aviso_garantia_urgente` (default 7) — nível "importante"

Auto-resolve quando garantia é renovada (dias > 30) ou usina perde garantia (filtro principal).

---

## ADR-015 — ConfiguracaoSistema como singleton no app `coleta`

**Data:** 2026-04-15.

**Decisão:** Modelo `ConfiguracaoSistema` dentro de `coleta/models.py` — padrão singleton (`pk=1` forçado no `save()`, `delete()` desabilitado, acessor `obter()`).

**Por quê:**
- Os parâmetros atuais (dias sem comunicação, meses de garantia, dias de aviso de garantia) estão diretamente ligados à coleta.
- Criar um app `core` novo por uma única tabela é overengineering — se o escopo crescer, migramos depois.
- Singleton com `obter()` + permissões gated no admin evita múltiplas linhas.

---

## ADR-016 — Sessão JWT "Gmail-style" (access 12h, refresh 90d com rotação)

**Data:** 2026-04-15.

**Contexto:** Os defaults do SimpleJWT (access de 5 min, refresh de 1 dia) forçavam login várias vezes por dia. Para um painel interno usado por poucos operadores, isso era atrito sem ganho real de segurança.

**Decisão:** `SIMPLE_JWT = { 'ACCESS_TOKEN_LIFETIME': 12h, 'REFRESH_TOKEN_LIFETIME': 90d, 'ROTATE_REFRESH_TOKENS': True, 'BLACKLIST_AFTER_ROTATION': True }`.

**Por quê:**
- Access de 12h cobre o dia de trabalho sem refresh.
- Refresh de 90d + rotação mantém sessão ativa indefinidamente enquanto o operador usar pelo menos 1x a cada 90 dias.
- Blacklist de refresh rotacionado protege contra reuso de token antigo.
- Endpoint `/api/auth/me/` retorna o perfil do usuário a cada carga, fornecendo `is_staff` confiável para decisões de UI.

---

## ADR-017 — Canal webhook para integrações externas

**Data:** 2026-04-15.

**Decisão:** Adicionado backend `notificacoes/backends/webhook.py` e expandido `ConfiguracaoNotificacao.CANAL_CHOICES` para incluir `'webhook'`. Faz POST JSON para cada URL nos destinatários, timeout de 10s, `is_disponivel()` sempre True (não exige env vars).

**Por quê:** Permite integrar facilmente com Slack/Discord (incoming webhooks), n8n, Zapier, ou endpoints internos — sem código novo para cada integração.

---

## ADR-018 — Ordenação de alertas por severidade

**Data:** 2026-04-15.

**Decisão:** `AlertaViewSet.get_queryset()` ordena por severidade primeiro, depois por `-inicio`, via `Case/When` na anotação `nivel_ordem` (crítico=0, importante=1, aviso=2, info=3). O frontend exibe data + hora juntas na coluna "Data".

**Por quê:** O operador sempre vê os alertas mais críticos primeiro, independentemente de ordenação cronológica.
