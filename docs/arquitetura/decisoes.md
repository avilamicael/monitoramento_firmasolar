---
title: Decisões de Arquitetura
tipo: decisoes
tags: [decisoes, arquitetura, adr]
---

# Decisões de Arquitetura

Registro de decisões técnicas não triviais tomadas no projeto. Formato: contexto → opções → decisão → motivo.

---

## ADR-001 — Monorepo com backend e frontend separados

**Contexto:** O sistema tem dois componentes com ciclos de vida diferentes: o backend Django (coleta e dados) e o Grafana (visualização).

**Opções:**
- Repositório único (monorepo)
- Dois repositórios separados

**Decisão:** Monorepo com pastas `backend_monitoramento/` e `frontend/`.

**Motivo:** A equipe é pequena (um desenvolvedor), os componentes são codependentes (Grafana lê o mesmo banco que o Django escreve) e o deploy é feito na mesma VPS. Um monorepo simplifica o versionamento e a referência cruzada entre componentes.

---

## ADR-002 — Grafana como camada de visualização (sem API REST própria)

**Contexto:** Precisávamos de dashboards operacionais. Opções incluíam construir uma SPA própria com API Django REST.

**Opções:**
- SPA React + API Django REST Framework
- Grafana com datasource PostgreSQL direto
- Metabase

**Decisão:** Grafana 10.4 com datasource PostgreSQL direto.

**Motivo:** Para monitoramento operacional (não produto para cliente final), Grafana entrega 95% do valor com 5% do esforço. Sem necessidade de manter API REST, autenticação de usuário final ou frontend. O Grafana acessa o PostgreSQL diretamente via rede Docker compartilhada (`firmasolar_obs`), eliminando um intermediário desnecessário.

---

## ADR-003 — Criptografia Fernet para credenciais no banco

**Contexto:** As credenciais de API dos provedores (API keys, senhas, tokens) precisam ser armazenadas de forma segura no banco PostgreSQL.

**Opções:**
- Armazenar em plaintext (inaceitável)
- Armazenar apenas em variáveis de ambiente (impossível para múltiplos provedores dinâmicos)
- Criptografia simétrica (Fernet/AES)
- Criptografia assimétrica (RSA)

**Decisão:** Fernet (da lib `cryptography`) com chave no `.env`.

**Motivo:** Fernet garante criptografia autenticada (AES-128-CBC + HMAC-SHA256). A chave fica apenas no `.env` (não no banco e não no repositório). Criptografia assimétrica seria desnecessariamente complexa para este caso — não há cenário onde encriptamos com uma chave e decriptamos com outra.

**Risco:** Se a `CHAVE_CRIPTOGRAFIA` for perdida, todas as credenciais armazenadas se tornam ilegíveis. Backup da chave é obrigatório.

---

## ADR-004 — Snapshots append-only com janela de 10 minutos

**Contexto:** Cada coleta gera dados de potência, energia e status de cada usina. Precisávamos decidir como armazenar o histórico.

**Opções:**
- Atualizar um único registro por usina (sem histórico)
- Inserir um snapshot a cada coleta (histórico completo)
- Time-series database (InfluxDB, TimescaleDB)

**Decisão:** Snapshots append-only no PostgreSQL, com `coletado_em` arredondado para janelas de 10 minutos.

**Motivo:** Histórico é essencial para análise de performance. PostgreSQL é suficiente para o volume atual (~130 usinas × 6 coletas/hora × 24h = ~18.000 registros/dia). O arredondamento para 10 min garante idempotência em retries sem criar duplicatas. Limpeza automática remove snapshots com mais de 90 dias via task diária.

---

## ADR-005 — Rate limiting distribuído via Redis

**Contexto:** Múltiplos workers Celery rodando em paralelo podem exceder os rate limits das APIs dos provedores se cada worker não "ver" as requisições dos outros.

**Opções:**
- Rate limiting por processo (sem compartilhamento)
- Rate limiting via banco de dados
- Rate limiting via Redis

**Decisão:** Redis com contador por janela deslizante.

**Motivo:** Redis é já parte da infraestrutura (broker do Celery). Operações atômicas garantem consistência entre workers sem locks de banco. Latência sub-milissegundo.

---

## ADR-006 — FusionSolar: intervalo mínimo de 900 segundos

**Contexto:** A API da Huawei FusionSolar retorna `failCode=407` (ACCESS_FREQUENCY_IS_TOO_HIGH) quando consultada com muita frequência. Inicialmente configuramos 2100s (35 min) por evidência empírica com um usuário compartilhado.

**Decisão:** Reduzido para 900s (15 min) com a criação do usuário dedicado `api_firmasolar`.

**Motivo:** A documentação oficial da Huawei especifica query interval de 15 minutos. O problema anterior era o usuário compartilhado (múltiplas integrações consumindo a mesma cota). Com usuário dedicado (1 API por usuário, recomendado pela Huawei), 15 min é suficiente.

**Observação:** O Celery Beat roda a cada 10 min. Com `min_intervalo_coleta_segundos=900`, a coleta do FusionSolar ocorre efetivamente a cada ~20 min (dois ciclos do Beat). Se o rate limit voltar, aumentar para 1800s.

---

## ADR-007 — WhiteNoise para arquivos estáticos

**Contexto:** Em produção com `DEBUG=False`, Django não serve arquivos estáticos. Precisávamos de uma solução para o Django Admin funcionar.

**Opções:**
- Configurar nginx para servir `/static/` direto do filesystem
- WhiteNoise (middleware que serve via Gunicorn)
- CDN externo (S3, CloudFront)

**Decisão:** WhiteNoise com `CompressedManifestStaticFilesStorage`.

**Motivo:** Para o escopo atual (apenas Django Admin acessado via SSH tunnel), a complexidade de configurar nginx para servir arquivos do container é desnecessária. WhiteNoise é zero-config, adiciona compressão gzip/brotli e cache busting via hash no nome do arquivo. CDN seria prematuro para este MVP.

---

## ADR-008 — Django Admin como interface de configuração (sem frontend próprio)

**Contexto:** É necessário gerenciar credenciais de provedores, catálogo de alarmes, supressões e configurações de notificação.

**Opções:**
- Construir frontend React + API REST
- Usar o Django Admin (personalizado)

**Decisão:** Django Admin com customizações específicas.

**Motivo:** O Django Admin é poderoso o suficiente para gerenciamento interno. A segurança é garantida pela exposição exclusiva via SSH tunnel (não está no nginx público). Construir um frontend separado seria trabalho de semanas sem valor adicional para o MVP.

---

## ADR-009 — Alertas com catálogo e supressão granular

**Contexto:** Provedores enviam dezenas de tipos diferentes de alarme. Alguns são ruidosos (alertas que aparecem constantemente mas não são acionáveis), outros são críticos.

**Decisão:** Sistema de três camadas:
1. `CatalogoAlarme` — define nível padrão e permite sobrescrever por operador
2. `RegraSupressao` — suprime um tipo de alarme globalmente ou por usina específica, com expiração opcional
3. `Alerta` — ocorrência vinculada ao catálogo

**Motivo:** Sem catálogo, o operador receberia spam de alertas não acionáveis. A supressão com expiração permite suprimir temporariamente durante manutenção. A granularidade por usina permite tratar casos especiais sem afetar toda a carteira.

---

## ADR-010 — Notificações sem restart (ConfiguracaoNotificacao no banco)

**Contexto:** As configurações de email e WhatsApp (destinatários, níveis a notificar) precisam ser alteráveis sem redeploy.

**Decisão:** `ConfiguracaoNotificacao` no banco, lida em tempo de execução a cada notificação.

**Motivo:** Alterações em variáveis de ambiente exigem restart dos containers. Para um sistema de alertas, o operador precisa conseguir adicionar um destinatário às 2h da manhã sem redeploy. O overhead de uma query extra a cada notificação é desprezível.
