# Architecture

**Analysis Date:** 2026-04-07

## Pattern Overview

**Overall:** Pipeline assíncrono orientado a eventos com adaptadores por provedor externo

**Key Characteristics:**
- Coleta de dados via tasks Celery agendadas (não há API REST — sem endpoints HTTP para negócio)
- Adaptador por provedor implementa interface ABC comum (`AdaptadorProvedor`), desacoplando o core da API de cada fabricante
- Ingestão atômica em transação única por ciclo, com notificações disparadas via `on_commit`
- Frontend é Grafana (read-only sobre o banco), sem camada de visualização própria

## Layers

**Provedores (Adaptadores externos):**
- Purpose: Normalizar dados crus de APIs externas (Solis, Hoymiles, FusionSolar) em dataclasses do sistema
- Location: `backend_monitoramento/provedores/`
- Contains: `base.py` (ABCs e dataclasses), `registro.py` (factory), `cripto.py`, `limitador.py`, `excecoes.py`, subpastas por provedor com `autenticacao.py`, `consultas.py`, `adaptador.py`
- Depends on: APIs REST externas dos fabricantes, Redis (rate limiting)
- Used by: `coleta/tasks.py`

**Coleta (Orquestração do ciclo):**
- Purpose: Coordenar a busca de dados de cada provedor, persistir tudo atomicamente e registrar o log
- Location: `backend_monitoramento/coleta/`
- Contains: `tasks.py` (Celery tasks), `ingestao.py` (ServicoIngestao), `models.py` (LogColeta)
- Depends on: `provedores/`, `usinas/`, `alertas/`, `notificacoes/tasks.py`
- Used by: Celery Beat (agendamento automático a cada 10 min)

**Usinas (Domínio de dados físicos):**
- Purpose: Persistência das entidades físicas e seus snapshots históricos
- Location: `backend_monitoramento/usinas/`
- Contains: `models.py` (Usina, SnapshotUsina, Inversor, SnapshotInversor)
- Depends on: `provedores.CredencialProvedor` (FK)
- Used by: `coleta/ingestao.py`, `alertas/`, Grafana (leitura direta no banco)

**Alertas (Domínio de eventos de problema):**
- Purpose: Ciclo de vida de alertas e catálogo de tipos de alarme; lógica de supressão
- Location: `backend_monitoramento/alertas/`
- Contains: `models.py` (CatalogoAlarme, RegraSupressao, Alerta), `categorizacao.py`, `supressao_inteligente.py`
- Depends on: `usinas.Usina` (FK)
- Used by: `coleta/ingestao.py`, `notificacoes/`

**Notificações (Despacho de avisos):**
- Purpose: Enviar alertas aos canais configurados (e-mail, WhatsApp) sem acoplar o envio ao ciclo de coleta
- Location: `backend_monitoramento/notificacoes/`
- Contains: `servico.py` (ServicoNotificacao), `tasks.py` (Celery task), `base.py` (ABC BackendNotificacao), `backends/email.py`, `backends/whatsapp.py`, `models.py` (ConfiguracaoNotificacao)
- Depends on: `alertas.Alerta`, SMTP/WhatsApp Evolution API
- Used by: `coleta/ingestao.py` (via `transaction.on_commit`)

**Config (Django settings e WSGI):**
- Purpose: Configuração do projeto, Celery Beat schedule, WSGI entry point
- Location: `backend_monitoramento/config/`
- Contains: `settings/base.py`, `settings/dev.py`, `settings/prod.py`
- Depends on: variáveis de ambiente
- Used by: todo o sistema

## Data Flow

**Ciclo de coleta (a cada 10 min via Celery Beat):**

1. `disparar_coleta_geral` (Celery Beat) itera `CredencialProvedor` ativas e dispara `coletar_dados_provedor.delay()` para cada uma
2. `coletar_dados_provedor` descriptografa credenciais (Fernet), monta o adaptador via `get_adaptador()`
3. Adaptador busca usinas em sequência; busca inversores em paralelo (`ThreadPoolExecutor`); busca alertas
4. Rate limiting por Redis (`LimitadorRequisicoes`) controla o ritmo antes de cada chamada HTTP
5. `ServicoIngestao` persiste tudo dentro de `transaction.atomic()`: upsert usina → snapshot usina → upsert inversor → snapshot inversor → `sincronizar_alertas()`
6. Para cada alerta novo ou escalado: `transaction.on_commit(enviar_notificacao_alerta.delay)`
7. Token de sessão (Hoymiles, FusionSolar) é salvo/atualizado no `CacheTokenProvedor` após o commit
8. `LogColeta` registra status, contagens e duração

**Fluxo de notificação (após commit da coleta):**

1. `enviar_notificacao_alerta` task carrega o `Alerta` do banco
2. Instancia `ServicoNotificacao`, que lê `ConfiguracaoNotificacao` ativo do banco
3. Para cada canal ativo com nível compatível, carrega o backend (`EmailBackend` ou `WhatsAppBackend`) e chama `enviar()`
4. Falha em um canal não impede os demais (try/except por canal)

**Estado dos alertas:**

`ativo` → `em_atendimento` (equipe assume manualmente) → `resolvido` (provedor para de reportar no próximo ciclo)

Alertas resolvidos que reaparecem são reabertos automaticamente (estado volta a `ativo`, `fim` é limpo).

## Key Abstractions

**AdaptadorProvedor (ABC):**
- Purpose: Contrato único que todos os provedores implementam; isola o core de qualquer API específica
- Examples: `provedores/solis/adaptador.py`, `provedores/hoymiles/adaptador.py`, `provedores/fusionsolar/adaptador.py`
- Pattern: ABC com métodos `buscar_usinas()`, `buscar_inversores()`, `buscar_alertas()`, propriedades `chave_provedor` e `capacidades`

**DadosUsina / DadosInversor / DadosAlerta (dataclasses):**
- Purpose: DTOs normalizados que fluem do adaptador para o ServicoIngestao; qualquer provedor produz exatamente o mesmo formato
- Examples: `provedores/base.py`
- Pattern: `@dataclass` Python com campos tipados e defaults explícitos

**CapacidadesProvedor (dataclass):**
- Purpose: Declarar em tempo de instância o que cada provedor suporta (inversores, alertas, alertas por conta vs. por usina, rate limits)
- Examples: `provedores/base.py`
- Pattern: consultado por `coletar_dados_provedor` para decidir estratégia de busca

**ServicoIngestao:**
- Purpose: Traduz DTOs do adaptador para operações ORM; garante idempotência por janela de 10 min
- Examples: `coleta/ingestao.py`
- Pattern: instanciado uma vez por ciclo de coleta; armazena `coletado_em` arredondado; usa `get_or_create` em todos os snapshots

**CatalogoAlarme:**
- Purpose: Registrar tipos de alarme por provedor; suporte a nivel sobrescrito pelo operador, supressão global e categorização automática
- Examples: `alertas/models.py`
- Pattern: auto-criado na primeira detecção (`criado_auto=True`); operador corrige via Django Admin

**LimitadorRequisicoes:**
- Purpose: Context manager que controla rate limit por provedor usando Redis como estado compartilhado entre workers
- Examples: `provedores/limitador.py`
- Pattern: incrementa contador no Redis antes de cada request HTTP; dorme se limite atingido

**BackendNotificacao (ABC):**
- Purpose: Interface para canais de notificação; nova integração não requer alteração no ServicoNotificacao
- Examples: `notificacoes/backends/email.py`, `notificacoes/backends/whatsapp.py`
- Pattern: `is_disponivel()` verifica presença de credenciais no settings; `enviar()` despacha

## Entry Points

**Celery Beat (agendamento):**
- Location: `coleta/tasks.py` — `disparar_coleta_geral`
- Triggers: automaticamente a cada 10 min; `renovar_tokens_provedores` a cada 6h; `limpar_snapshots_antigos` diariamente às 3h
- Responsibilities: fanout de coletas por credencial ativa

**Celery Worker (execução):**
- Location: `coleta/tasks.py` — `coletar_dados_provedor`; `notificacoes/tasks.py` — `enviar_notificacao_alerta`
- Triggers: mensagens no broker Redis
- Responsibilities: coleta completa de um provedor; envio de notificações

**Django Admin:**
- Location: `config/urls.py` → `/admin/`
- Triggers: acesso HTTP do operador
- Responsibilities: gerenciar credenciais, catálogo de alarmes, regras de supressão, configuração de notificações, visualização de logs

**manage.py:**
- Location: `backend_monitoramento/manage.py`
- Triggers: invocação CLI
- Responsibilities: migrations, comandos customizados (`fusionsolar_credenciais`, `setup_whatsapp`)

## Error Handling

**Strategy:** Exceções tipadas por categoria; retry automático via Celery para erros transitórios; falhas de autenticação marcam credencial sem retry

**Patterns:**
- `ProvedorErroAuth` → sem retry, credencial marcada como `precisa_atencao=True`
- `ProvedorErroRateLimit` → sem retry (aguarda próximo ciclo do Beat); token salvo mesmo em falha para evitar re-login desnecessário no próximo ciclo
- `ProvedorErro` genérico → retry Celery (max 3, intervalo 60s)
- Falha em inversores de uma usina específica → registrado como warning, as demais usinas seguem normalmente
- Falha em um canal de notificação → logged como error, demais canais continuam

## Cross-Cutting Concerns

**Logging:** `logging.getLogger(__name__)` em cada módulo; níveis info/warning/error/debug; sem framework externo; logs acessíveis via `docker compose logs`

**Validation:** Feita nos adaptadores ao normalizar os DTOs; valores ausentes recebem defaults seguros (0.0, strings vazias, dict vazio); erros de parse resultam em dados neutros, nunca exceção

**Authentication:** Acesso ao Django Admin via autenticação Django padrão; credenciais de provedores criptografadas com Fernet antes de entrar no banco (`provedores/cripto.py`); chave em variável de ambiente `CHAVE_CRIPTOGRAFIA`

**Idempotência:** Snapshots usam `get_or_create` com `coletado_em` arredondado para janelas de 10 min — duas coletas na mesma janela produzem exatamente 1 snapshot

**Multi-provedor:** Cada `CredencialProvedor` pertence a exatamente um provedor; todas as queries de alertas e usinas são filtradas por provedor/credencial; sem risco de vazamento cross-provedor

---

*Architecture analysis: 2026-04-07*
