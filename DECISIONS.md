# DECISIONS.md

Registro de decisões de arquitetura não triviais.

---

## 2026-04-15 — Alertas internos restritos a usinas com garantia ativa

**Contexto**
Em produção, o sistema estava monitorando 131 usinas, incluindo várias sem comunicação há 15–580 dias. Isso gerava alertas ruidosos de "sem comunicação" e "sem geração" para usinas que o cliente final provavelmente abandonou ou nunca contratou serviço de monitoramento.

**Opções consideradas**
- (A) Filtrar na coleta — não coletar usinas sem garantia. Perde histórico se garantia for renovada.
- (B) Filtrar apenas na geração de alertas internos — continua coletando, dashboard tem os dados, alertas só para quem paga.
- (C) Flag explícita por usina, independente de garantia.

**Decisão**
Opção **B** — coletamos todas as usinas (dashboard precisa dos dados), mas `alertas/analise.py` só gera alertas para usinas com `GarantiaUsina.ativa=True`. Usinas sem garantia ou com garantia expirada continuam populando snapshots.

**Por quê**
Separa duas responsabilidades: **coleta de dados** (todas) versus **alertamento operacional** (apenas garantia ativa). Permite no futuro um dashboard "com garantia vs sem garantia" sem nova migração.

---

## 2026-04-15 — Auto-criação de garantia de 12 meses na primeira coleta

**Contexto**
Regra de negócio: toda usina nova entra com 12 meses de garantia contando da data em que é registrada pela primeira vez no sistema. Depois de 12 meses, o cliente precisa renovar explicitamente.

**Decisão**
`ServicoIngestao.upsert_usina()` cria `GarantiaUsina(data_inicio=hoje, meses=config.meses_garantia_padrao)` quando a Usina é criada pela primeira vez. Usa `get_or_create` para ser idempotente — se já existir garantia (caso raro de race condition ou criação manual), não sobrescreve.

**Por quê**
- Coleta é o único ponto onde usinas nascem no sistema. Hook ali garante cobertura 100%.
- `data_inicio = hoje` (data do primeiro registro) é a interpretação correta: 12m a partir de quando começamos a monitorar.
- `meses_garantia_padrao` configurável evita hardcode da regra de negócio.

---

## 2026-04-15 — Auto-pausa de usinas sem comunicação

**Contexto**
Usinas que param de comunicar por Wi-Fi (às vezes por anos) continuavam gerando tentativas de coleta, ruído de alertas e consumo de quota de API dos provedores.

**Decisão**
Antes de cada ciclo de coleta de um provedor, `_pausar_usinas_inativas()` marca `ativo=False` em toda usina cujo `ultimo_snapshot.coletado_em` seja mais antigo que `ConfiguracaoSistema.dias_sem_comunicacao_pausar` (padrão 60 dias). No loop principal, usinas com `ativo=False` são puladas — nem snapshot nem alertas do provedor são criados para elas.

**Por quê**
- Reativação é manual (via admin) — usuário decide caso a caso. Evita ping-pong automático.
- Valor configurável (não hardcoded) — operador ajusta conforme a realidade da carteira.
- Checagem por ciclo (não job separado) — sem infra adicional.

---

## 2026-04-15 — Alerta de garantia próxima do fim

**Contexto**
Usinas no sistema entram com garantia de 12 meses. Sem aviso prévio, a garantia expira silenciosamente, atendimento e renovação ficam reativos.

**Decisão**
Novo alerta interno `garantia_expirando`, gerado por `_verificar_garantia_expirando()` a cada ciclo de coleta. Dois patamares configuráveis em `ConfiguracaoSistema`:
- `dias_aviso_garantia_proxima` (padrão 30) — nível "aviso"
- `dias_aviso_garantia_urgente` (padrão 7) — nível "importante"

Auto-resolve quando: garantia renovada (dias_restantes > 30) ou usina perde a garantia (ativa=False — aí o filtro principal para de gerar alertas).

**Por quê**
- Reaproveita pipeline existente (`_enriquecer_ou_criar` / `_resolver_alerta_interno`) — sem infra nova.
- Patamares configuráveis evitam hardcode de regra comercial (prazos podem mudar).
- Notificação (WhatsApp/email) virá depois — por enquanto só o alerta no painel.

---

## 2026-04-15 — ConfiguracaoSistema como singleton no app `coleta`

**Contexto**
Decidiu-se tornar dois parâmetros de negócio configuráveis: dias até pausar por inatividade e meses de garantia padrão.

**Opções consideradas**
- Criar um app `core` dedicado para configuração global.
- Reaproveitar um app existente.

**Decisão**
Modelo `ConfiguracaoSistema` dentro de `coleta/models.py`, com padrão singleton (`pk=1` forçado no `save()`, `delete()` desabilitado, acessor `obter()` que cria na primeira chamada).

**Por quê**
- Os dois parâmetros atuais estão diretamente ligados à coleta. Criar um app novo por uma única tabela é overengineering.
- Singleton com `obter()` + admin com `has_add_permission` gated evita estados inconsistentes (múltiplas linhas).
- Se o escopo crescer (notificações, dashboard, etc.), migramos para um app `core` depois.
