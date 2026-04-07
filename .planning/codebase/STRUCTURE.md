# Codebase Structure

**Analysis Date:** 2026-04-07

## Directory Layout

```
firmasolar/                          # Raiz do repositório
├── backend_monitoramento/           # Projeto Django + Celery (todo o backend)
│   ├── config/                      # Configuração Django (settings, urls, wsgi, celery)
│   │   └── settings/                # Settings divididos por ambiente
│   │       ├── base.py              # Configuração compartilhada
│   │       ├── dev.py               # Overrides para desenvolvimento local
│   │       └── prod.py              # Overrides para produção
│   ├── provedores/                  # App: adaptadores de provedores externos
│   │   ├── base.py                  # ABCs e dataclasses (contrato do sistema)
│   │   ├── registro.py              # Factory: get_adaptador()
│   │   ├── cripto.py                # Criptografia Fernet de credenciais
│   │   ├── limitador.py             # Rate limiter via Redis
│   │   ├── excecoes.py              # Hierarquia de exceções
│   │   ├── models.py                # CredencialProvedor, CacheTokenProvedor
│   │   ├── solis/                   # Adaptador Solis Cloud
│   │   │   ├── autenticacao.py      # HMAC-SHA1 stateless
│   │   │   ├── consultas.py         # Chamadas HTTP à API Solis
│   │   │   └── adaptador.py         # SolisAdaptador (normalização)
│   │   ├── hoymiles/                # Adaptador Hoymiles S-Cloud
│   │   │   ├── autenticacao.py      # Login com cookie de sessão
│   │   │   ├── consultas.py         # Chamadas HTTP à API Hoymiles
│   │   │   └── adaptador.py         # HoymilesAdaptador (normalização)
│   │   ├── fusionsolar/             # Adaptador Huawei FusionSolar
│   │   │   ├── autenticacao.py      # Login com XSRF token
│   │   │   ├── consultas.py         # Chamadas HTTP à API FusionSolar
│   │   │   └── adaptador.py         # FusionSolarAdaptador (normalização)
│   │   └── management/commands/
│   │       └── fusionsolar_credenciais.py  # CLI para configurar credenciais FusionSolar
│   ├── coleta/                      # App: orquestração do ciclo de coleta
│   │   ├── tasks.py                 # Tasks Celery: disparar_coleta_geral, coletar_dados_provedor, limpeza
│   │   ├── ingestao.py              # ServicoIngestao: upsert + snapshots + sincronizar_alertas
│   │   └── models.py                # LogColeta: auditoria de cada ciclo
│   ├── usinas/                      # App: entidades físicas e séries temporais
│   │   └── models.py                # Usina, SnapshotUsina, Inversor, SnapshotInversor
│   ├── alertas/                     # App: gestão de alertas e catálogo de alarmes
│   │   ├── models.py                # CatalogoAlarme, RegraSupressao, Alerta
│   │   ├── categorizacao.py         # Inferência automática de categoria de alarme
│   │   └── supressao_inteligente.py # Detecção de desligamento gradual (pôr do sol)
│   ├── notificacoes/                # App: despacho de notificações
│   │   ├── servico.py               # ServicoNotificacao: despacha para canais ativos
│   │   ├── tasks.py                 # Task Celery: enviar_notificacao_alerta
│   │   ├── base.py                  # ABC BackendNotificacao, DadosNotificacao
│   │   ├── models.py                # ConfiguracaoNotificacao (gerenciado pelo admin)
│   │   ├── backends/
│   │   │   ├── email.py             # EmailBackend (SMTP via Django)
│   │   │   └── whatsapp.py          # WhatsAppBackend (Evolution API ou Meta)
│   │   └── management/commands/
│   │       └── setup_whatsapp.py    # CLI para configurar instância WhatsApp
│   ├── requirements/                # Dependências Python separadas por ambiente
│   ├── manage.py                    # Entry point CLI Django
│   ├── Dockerfile                   # Imagem do backend (web, celery, beat)
│   ├── docker-compose.yml           # Orquestração: db, redis, web, celery, beat, evolution-api
│   └── pytest.ini                   # Configuração de testes
├── frontend/
│   └── grafana/                     # Dashboards e provisioning do Grafana
│       ├── dashboards/              # JSONs dos dashboards (principal, detalhes)
│       └── provisioning/            # Configuração automática de datasources e dashboards
├── data/                            # Volumes persistentes (não commitados)
│   ├── postgres/                    # Dados do PostgreSQL
│   ├── redis/                       # Dados do Redis
│   ├── grafana/                     # Dados do Grafana
│   └── evolution/                   # Instâncias do Evolution API (WhatsApp)
└── docs/                            # Documentação técnica do projeto
    ├── arquitetura/                  # Visão geral, fluxo de coleta, decisões
    ├── modulos/                      # Documentação por módulo
    ├── provedores/                   # Documentação por provedor externo
    ├── grafana/                      # Documentação dos dashboards
    ├── infraestrutura/               # Documentação de deploy e infra
    └── operacional/                  # Guias operacionais
```

## Directory Purposes

**`backend_monitoramento/provedores/`:**
- Purpose: Tudo relacionado a provedores externos — modelos, criptografia, rate limiting e os três adaptadores concretos
- Contains: ABC + dataclasses em `base.py`; factory em `registro.py`; uma subpasta por provedor com a tríade `autenticacao.py` / `consultas.py` / `adaptador.py`
- Key files: `base.py`, `registro.py`, `cripto.py`, `limitador.py`, `excecoes.py`

**`backend_monitoramento/coleta/`:**
- Purpose: Orquestração do ciclo de 10 minutos; single responsibility — coordenar, não implementar
- Contains: tasks Celery, ServicoIngestao, LogColeta
- Key files: `tasks.py`, `ingestao.py`

**`backend_monitoramento/usinas/`:**
- Purpose: Domínio de dados físicos — sem lógica de negócio, apenas modelos e migrations
- Contains: apenas `models.py` e `admin.py`
- Key files: `models.py`

**`backend_monitoramento/alertas/`:**
- Purpose: Domínio de alertas com lógica de negócio: catálogo, supressão, ciclo de vida
- Contains: modelos, categorizacao, supressao_inteligente
- Key files: `models.py`, `categorizacao.py`, `supressao_inteligente.py`

**`backend_monitoramento/notificacoes/`:**
- Purpose: Despacho desacoplado de notificações; novos canais = novo backend sem tocar no core
- Contains: serviço central, task Celery, ABC, modelos de configuração, backends concretos
- Key files: `servico.py`, `tasks.py`, `base.py`, `backends/email.py`, `backends/whatsapp.py`

**`backend_monitoramento/config/settings/`:**
- Purpose: Settings Django divididos por ambiente; base.py contém tudo, dev.py e prod.py apenas overrides
- Key files: `base.py` (Celery, banco, criptografia, notificações)

**`frontend/grafana/`:**
- Purpose: Dashboards Grafana provisionados automaticamente (sem UI própria no backend)
- Contains: JSONs de dashboards em `dashboards/`, configs YAML em `provisioning/`

**`data/`:**
- Purpose: Volumes Docker persistentes — nunca commitados no git
- Generated: Yes (criados pelo Docker)
- Committed: No

## Key File Locations

**Entry Points:**
- `backend_monitoramento/manage.py`: CLI Django (migrations, comandos)
- `backend_monitoramento/coleta/tasks.py`: entry points de execução async (Celery)
- `backend_monitoramento/config/settings/base.py`: configuração raiz do sistema

**Configuration:**
- `backend_monitoramento/config/settings/base.py`: Celery Beat schedule, banco, Redis, criptografia, notificações
- `backend_monitoramento/config/settings/dev.py`: overrides locais
- `backend_monitoramento/config/settings/prod.py`: overrides de produção
- `backend_monitoramento/docker-compose.yml`: orquestração de containers
- `backend_monitoramento/.env.example`: template de variáveis de ambiente

**Core Logic:**
- `backend_monitoramento/provedores/base.py`: contrato do sistema (ABCs + dataclasses)
- `backend_monitoramento/provedores/registro.py`: factory de adaptadores
- `backend_monitoramento/coleta/ingestao.py`: ServicoIngestao (persistência atômica)
- `backend_monitoramento/coleta/tasks.py`: orquestração do ciclo de coleta
- `backend_monitoramento/alertas/supressao_inteligente.py`: lógica de supressão contextual

**Models:**
- `backend_monitoramento/usinas/models.py`: Usina, SnapshotUsina, Inversor, SnapshotInversor
- `backend_monitoramento/alertas/models.py`: CatalogoAlarme, RegraSupressao, Alerta
- `backend_monitoramento/provedores/models.py`: CredencialProvedor, CacheTokenProvedor
- `backend_monitoramento/coleta/models.py`: LogColeta
- `backend_monitoramento/notificacoes/models.py`: ConfiguracaoNotificacao

**Testing:**
- `backend_monitoramento/alertas/test_supressao_inteligente.py`: testes de supressão inteligente
- `backend_monitoramento/pytest.ini`: configuração de testes

## Naming Conventions

**Files:**
- Snake case para todos os arquivos Python: `ingestao.py`, `supressao_inteligente.py`, `categorizacao.py`
- Nomes descritivos sem sufixos desnecessários: `servico.py` (não `notification_service.py`), `base.py` (não `abstract.py`)
- Backends de notificação pelo nome do canal: `email.py`, `whatsapp.py`

**Directories:**
- Snake case em português: `provedores/`, `usinas/`, `alertas/`, `notificacoes/`, `coleta/`
- Subpastas de provedores pelo nome do produto: `solis/`, `hoymiles/`, `fusionsolar/`

**Classes:**
- PascalCase em português: `ServicoIngestao`, `AdaptadorProvedor`, `LimitadorRequisicoes`, `ServicoNotificacao`
- Adaptadores concretos: `{Provedor}Adaptador` (ex: `SolisAdaptador`)
- Exceções: `Provedor{Tipo}` (ex: `ProvedorErroAuth`)
- Dataclasses: `Dados{Entidade}` (ex: `DadosUsina`, `DadosInversor`)

**Functions/Methods:**
- Snake case em português: `buscar_usinas()`, `sincronizar_alertas()`, `e_desligamento_gradual()`
- Tasks Celery: verbo de ação no infinitivo: `disparar_coleta_geral`, `coletar_dados_provedor`, `enviar_notificacao_alerta`

## Where to Add New Code

**Novo provedor de monitoramento:**
1. Criar `backend_monitoramento/provedores/{nome_provedor}/` com `autenticacao.py`, `consultas.py`, `adaptador.py`
2. Implementar `AdaptadorProvedor` ABC em `adaptador.py`
3. Registrar em `backend_monitoramento/provedores/registro.py` no dict `REGISTRO`
4. Adicionar em `PROVEDORES` em `backend_monitoramento/provedores/models.py`
5. Adicionar rate limits em `backend_monitoramento/provedores/limitador.py`

**Novo canal de notificação:**
1. Criar `backend_monitoramento/notificacoes/backends/{canal}.py` implementando `BackendNotificacao`
2. Registrar no `_BACKENDS_MAP` em `backend_monitoramento/notificacoes/servico.py`
3. Adicionar em `CANAL_CHOICES` em `backend_monitoramento/notificacoes/models.py`

**Nova lógica de supressão:**
- Domínio: `backend_monitoramento/alertas/supressao_inteligente.py`
- Integrar em `backend_monitoramento/coleta/ingestao.py` no método `sincronizar_alertas()`

**Nova task agendada:**
- Implementar em `backend_monitoramento/coleta/tasks.py` (se relacionada a coleta) ou no app correspondente
- Registrar no `CELERY_BEAT_SCHEDULE` em `backend_monitoramento/config/settings/base.py`

**Novo modelo de dados:**
- Adicionar no `models.py` do app correspondente
- Criar migration com `manage.py makemigrations`
- Registrar no `admin.py` para visibilidade no Django Admin

**Utilitários compartilhados:**
- Dentro do app mais coeso com a funcionalidade (ex: `provedores/cripto.py`, `alertas/categorizacao.py`)
- Sem diretório `utils/` genérico — cada módulo carrega seus próprios helpers

## Special Directories

**`data/`:**
- Purpose: Volumes persistentes dos serviços Docker (postgres, redis, grafana, evolution)
- Generated: Yes (pelo Docker em primeira execução)
- Committed: No (listado em `.gitignore`)

**`frontend/grafana/`:**
- Purpose: Configuração declarativa do Grafana (dashboards e provisioning)
- Generated: No (mantido manualmente)
- Committed: Yes

**`backend_monitoramento/*/migrations/`:**
- Purpose: Histórico de migrations Django por app
- Generated: Yes (via `manage.py makemigrations`)
- Committed: Yes (crítico — define o schema do banco)

**`.planning/`:**
- Purpose: Documentos de planejamento e mapeamento do codebase (uso interno de ferramentas)
- Generated: No
- Committed: Yes

---

*Structure analysis: 2026-04-07*
