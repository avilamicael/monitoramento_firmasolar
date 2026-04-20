# DECISIONS.md

Registro de decisões de arquitetura não triviais.

---

## 2026-04-20 — Alertas: um registro por evento, nunca reabrir resolvido

**Contexto**
O comportamento anterior reabria o mesmo `Alerta` sempre que uma condição previamente resolvida voltava a ocorrer: `estado` ia de `resolvido` → `ativo`, `fim` era limpo. Dois problemas práticos:

1. **Perda de histórico.** Se a tensão da usina oscilava 10 vezes ao dia, o cliente via um único alerta antigo com `inicio = 15/04`, não 10 alertas com `fim` preenchido. Impossível contar quantos picos aconteceram no mês para relatório.
2. **`atualizado_em` congelado.** `Alerta.objects.filter().update()` não dispara `auto_now=True` no Django — o campo ficava parado na data de criação mesmo quando o alerta era reconfirmado ou resolvido/reaberto. Do ponto de vista da UI, parecia que o alerta estava "preso", quando na verdade era silenciosamente reativado a cada ciclo.

Na usina Agripino Teixeira (Hoymiles), os alertas `g_warn` e `l3_warn` estavam ativos desde 15/04 com `atualizado_em` idêntico, mas o provedor os reconfirmava a cada 10 min. Parecia bug visual; era perda de evidência.

**Decisão**
Mudança dupla, aplicada a alertas internos (`_enriquecer_ou_criar` em `alertas/analise.py`) e alertas de provedor (`sincronizar_alertas` em `coleta/ingestao.py`):

1. **Nunca reabrir alerta resolvido.** Se a condição some e volta, cria um NOVO `Alerta`. Invariante mantido por lógica (e pelo próprio `unique_together`): existe no máximo 1 ativo por (usina, categoria) para internos e (usina, catalogo_alarme) para provedor.
2. **Sufixo de timestamp no `id_alerta_provedor`.** Cada novo alerta ganha `{chave}_{YYYYMMDDTHHMMSSffffffZ}` — garante unicidade sem colidir com o resolvido anterior de mesmo prefixo. A constraint `(usina, id_alerta_provedor)` continua válida.
3. **`atualizado_em` passa a ser atualizado explicitamente** em todo `.update()` que toca um Alerta (não podemos depender do `auto_now=True`).
4. **Resolução por desaparecimento em provedores** passa a rastrear PKs tocados no ciclo (set `pks_tocados`) em vez de comparar `id_alerta_provedor` literal — necessário porque o ID muda a cada evento.

O parâmetro `chave` em `_resolver_alerta_interno` ficou vestigial (categoria + origem já identificam); mantive aceitando o argumento para não quebrar os ~10 call sites, mas sem usá-lo.

**Por quê**
- Relatórios ("quantas vezes a usina X teve sobretensão em abril?") viram uma query trivial: `count()` por `(usina, categoria, origem='interno')` com filtro de data em `inicio`.
- Duração real de cada incidente fica preservada em `fim - inicio` — antes, a "duração" após reabrir era cumulativa de múltiplos eventos.
- UI mostra `atualizado_em` correto — operador sabe quando foi a última confirmação do alerta vs. quando começou.

**Limitação**
- Um tipo que "pisca" muito gera muitos alertas (1 por evento). Mitigação: na phase seguinte (histerese + persistência para sobretensão) já reduz drasticamente o piscar. Outras categorias oscilantes (`tensao_zero`, `corrente_baixa`) têm suas próprias regras de persistência.
- Não migramos alertas históricos. Registros antigos continuam com `atualizado_em` congelado — só novos eventos a partir deste commit seguem a regra nova.

---

## 2026-04-20 — Sobretensão: histerese + persistência de 3 coletas

**Contexto**
A regra antiga `tensao_ac_v >= limite` abria o alerta e `< limite` resolvia em uma única coleta. Como a tensão AC oscila naturalmente (exemplo real: 225V → 241V → 228V → 238V → 241V em 6h), o alerta ficava ligando e desligando a cada ciclo — sem ninguém perceber, porque `atualizado_em` ficava congelado (ver ADR acima).

Um inversor com tensão efetivamente estável a 241V gerava alerta contínuo (0,5% acima do limite, ruído de rede normal). O operador perdia confiança no alerta.

**Decisão**
Em `alertas/analise.py`:

1. **Detecção**: `tensao > limite` (era `>=`). Igual ao limite conta como normal — só "passar do valor estipulado" é anormal.
2. **Persistência**: abre o alerta apenas após 3 coletas consecutivas com pelo menos 1 inversor acima do limite; fecha apenas após 3 coletas consecutivas com todos os inversores iguais ou abaixo do limite. Oscilação intermediária mantém o estado atual.
3. Constante `SOBRETENSAO_N_COLETAS = 3` no topo do módulo (fácil de ajustar no futuro).

A persistência é medida por SnapshotUsina como marcador de ciclo, cruzando com SnapshotInversor em janela de 5 min. 3 queries por análise (1 para timestamps + 2 para consultas — a atual já foi salva quando a função roda).

**Por quê**
- A decisão do usuário: "se passar do valor estipulado para aquela usina, já tem que dar sobretensão. Se o valor for abaixo, independente de qual seja abaixo, igual ou abaixo do valor estipulado para a usina, aí pode voltar ao normal."
- 3 coletas (~30 min de janela) é suficiente para filtrar picos momentâneos sem deixar passar sobretensão sustentada.
- O valor de `tensao_sobretensao_v` é por usina (configurável no admin) — cobre o caso de localidades com tensão nominal mais alta (ex: rede que opera naturalmente em 242V).

**Não alterado**
- `tensao_zero`: mantida a regra atual (zero em qualquer momento). Usuário pediu para não mexer nesta categoria.
- `corrente_baixa`: mantida a regra de 2h (já tinha sua própria persistência).

---

## 2026-04-20 — Hoymiles: usar `last_data_time` como `data_medicao` e suprimir `s_uoff` quando antigo

**Contexto**
Em produção, 3 usinas Hoymiles estavam com alerta crítico "Sistema desligado" (`s_uoff`), mas duas delas não reportavam dado algum desde novembro de 2025 (~5 meses). Inspecionando o `payload_bruto`, o `last_data_time` da Hoymiles mostrava claramente que o DTU estava offline há meses — o cenário real é Wi-Fi/datalogger desconectado, não sistema desligado. O adaptador, porém:

1. Preenchia `data_medicao=datetime.now()` ignorando `last_data_time`, o que fazia `_verificar_sem_comunicacao` (em `alertas/analise.py`) nunca disparar para Hoymiles.
2. Propagava `s_uoff=true` como alerta crítico independentemente da idade do último dado recebido.

Resultado prático: dois alertas conflitantes coexistiam (ou só o crítico, que é enganoso) e o cliente recebia "Sistema desligado" quando o caso real era falha de comunicação.

**Opções consideradas**
- (A) Parsear `last_data_time` no `data_medicao` e manter `s_uoff` sempre emitindo. Resolve o alerta interno `sem_comunicacao`, mas continuaríamos com dois alertas redundantes para o mesmo incidente.
- (B) **Parsear `last_data_time` + suprimir `s_uoff` quando `agora - last_data_time > 24h`.** O alerta externo só representa desligamento real (com dado recente); o caso Wi-Fi fica com o alerta interno `sem_comunicacao` (que já existe e tem sugestão adequada).
- (C) Rebaixar `s_uoff` antigo de `critico` para `aviso`. Não resolve a ambiguidade — continuaríamos chamando de "Sistema desligado" o que é "sem comunicação".

**Decisão**
Opção **B**. A regra é: dentro de 24h de comunicação → desligamento real, crítico, alerta externo. Mais que 24h sem comunicação → responsabilidade do alerta interno `sem_comunicacao`, com sugestão "Verificar Wi-Fi/datalogger". Mudanças em `provedores/hoymiles/adaptador.py`:

- Novo helper `_parsear_data_medicao(realtime, tz_nome)` converte `last_data_time`/`data_time` (naive no fuso da usina) para UTC.
- Cache `_ultima_comunicacao_por_usina` populado em `buscar_usinas()` e consultado em `buscar_alertas()` — ambos rodam no mesmo ciclo de coleta (ordem garantida em `coleta/tasks.py`).
- `_extrair_alertas` suprime a flag `s_uoff` (e **só** ela) quando a última comunicação está acima do limite.

Threshold 24h alinhado com `_verificar_sem_comunicacao` em `alertas/analise.py:269`.

**Por quê**
- O alerta de "Sistema desligado" precisa ser acionável: operador reage diferente de desligamento real (visita técnica, disjuntores) vs. Wi-Fi offline (contato com cliente, orientação remota).
- `last_data_time` é o ground truth da comunicação — já está no payload, só não estava sendo usado.
- Cache de ciclo evita nova chamada HTTP no endpoint de realtime dentro de `buscar_alertas`.
- Só `s_uoff` é afetado; outras flags (`dl`, `g_warn`, etc.) continuam como estavam.

**Limitação conhecida**
`_normalizar_inversor` ainda usa `datetime.now()` para `data_medicao` do inversor — os dados de `baixar_dados_dia` não expõem timestamp por microinversor de forma trivial. Fora do escopo desta correção; não afeta o alerta `sem_comunicacao`, que usa o snapshot da usina.

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
