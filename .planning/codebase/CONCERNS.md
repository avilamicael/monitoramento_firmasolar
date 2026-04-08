# Codebase Concerns

**Analysis Date:** 2026-04-07

---

## Tech Debt

**Provedor `solarman` declarado mas não implementado:**
- Issue: `CredencialProvedor.PROVEDORES` lista `('solarman', 'Solarman Pro')` e `limitador.py` tem entradas para `solarman`, mas não existe pasta `provedores/solarman/` nem adaptador correspondente. O `get_adaptador()` lançaria `ValueError` se um operador criasse uma credencial `solarman` pelo admin.
- Files: `backend_monitoramento/provedores/models.py:14`, `backend_monitoramento/provedores/limitador.py:16`, `backend_monitoramento/provedores/registro.py`
- Impact: Erro de runtime silencioso — a coleta falharia apenas na task Celery, com mensagem genérica no log, sem aviso no admin.
- Fix approach: Remover `solarman` de `PROVEDORES` e de `LIMITES` até o adaptador ser implementado, ou criar stub mínimo com `NotImplementedError`.

**Duas consultas N+1 de supressão dentro do loop de alertas:**
- Issue: Em `sincronizar_alertas()`, para cada alerta com `id_tipo_alarme_provedor`, são feitas 2 queries ao banco (`RegraSupressao.objects.filter(...escopo='todas'...).exists()` e `RegraSupressao.objects.filter(...escopo='usina'...).exists()`). Com muitos alertas ativos, isso resulta em 2×N queries por ciclo de coleta.
- Files: `backend_monitoramento/coleta/ingestao.py:199-214`
- Impact: Performance degradada progressivamente conforme o volume de alertas e regras de supressão crescem. O ciclo de ingestão já roda dentro de uma transação longa.
- Fix approach: Pré-carregar todas as regras de supressão ativas em um dict/set antes do loop, indexado por `(catalogo_id, escopo, usina_id)`, e fazer lookup em memória.

**Query de verificação `ja_aberto` também dentro do loop de alertas:**
- Issue: Para alertas do tipo `sistema_desligado`, é feita uma query `Alerta.objects.filter(...).exists()` por alerta, ainda dentro do mesmo loop em `sincronizar_alertas()`.
- Files: `backend_monitoramento/coleta/ingestao.py:224-228`
- Impact: Queries adicionais para cada alerta do tipo `sistema_desligado`. Em usinas com microinversores Hoymiles, onde `s_uoff` é o alerta mais comum, isso se acumula rapidamente.
- Fix approach: Pré-carregar IDs de alertas abertos do tipo `sistema_desligado` antes do loop.

**`limpar_snapshots_antigos` deleta sem paginação:**
- Issue: `SnapshotUsina.objects.filter(coletado_em__lt=corte).delete()` e `SnapshotInversor.objects.filter(coletado_em__lt=corte).delete()` fazem DELETE em massa irrestrito. Com meses de dados acumulados, a primeira execução pode demorar minutos e travar a tabela.
- Files: `backend_monitoramento/coleta/tasks.py:275-276`
- Impact: Lock de tabela prolongado às 3h da manhã; pode causar timeout de coletas noturnas. Inaceitável conforme o volume cresce.
- Fix approach: Implementar deleção em lotes (`LIMIT 1000` em loop com `time.sleep(0.1)` entre batches) para minimizar lock time.

**`_para_float` duplicado em três adaptadores:**
- Issue: A função `_para_float(valor) -> float` com exatamente a mesma implementação existe em `fusionsolar/adaptador.py:16`, `hoymiles/adaptador.py:35`, e `solis/adaptador.py:13`.
- Files: `backend_monitoramento/provedores/fusionsolar/adaptador.py:16`, `backend_monitoramento/provedores/hoymiles/adaptador.py:35`, `backend_monitoramento/provedores/solis/adaptador.py:13`
- Impact: Qualquer bug ou necessidade de mudança precisa ser aplicada em três lugares.
- Fix approach: Mover para `provedores/base.py` ou um módulo `provedores/utils.py` e importar nos adaptadores.

**`disparar_coleta_geral` não carrega credenciais com `select_related`:**
- Issue: `CredencialProvedor.objects.filter(ativo=True)` carrega apenas as credenciais. A task `coletar_dados_provedor` então faz acesso a `credencial.cache_token` (OneToOne) gerando queries adicionais por credencial.
- Files: `backend_monitoramento/coleta/tasks.py:33`, `backend_monitoramento/coleta/tasks.py:73-77`
- Impact: N+1 queries na carga de tokens em cache, uma por provedor ativo. Baixo impacto hoje (3 provedores), mas cresce linearmente.
- Fix approach: `CredencialProvedor.objects.filter(ativo=True).prefetch_related('cache_token')` no `coletar_dados_provedor`.

---

## Known Bugs

**`nivel_efetivo` usa `nivel_padrao` independente de `nivel_sobrescrito`:**
- Symptoms: O campo `nivel_efetivo` da propriedade em `CatalogoAlarme` sempre retorna `nivel_padrao`, e o código em `sincronizar_alertas()` replica esse comportamento (linha 218: `if catalogo.nivel_sobrescrito: nivel_efetivo = catalogo.nivel_padrao`). A lógica de sobrescrita parece correta na coleta mas a propriedade do model é um no-op (retorna sempre `nivel_padrao`).
- Files: `backend_monitoramento/alertas/models.py:82-84`, `backend_monitoramento/coleta/ingestao.py:217-218`
- Trigger: A propriedade `nivel_efetivo` nunca diferencia o caso sobrescrito do padrão porque sempre retorna `nivel_padrao`. Se algo no sistema usar `catalogo.nivel_efetivo` esperando a semântica documentada, terá comportamento incorreto.
- Workaround: A coleta não usa a propriedade — trata o caso manualmente. Mas a propriedade é enganosa para qualquer código futuro.

**Alerta Hoymiles sem `energia_total_kwh`:**
- Symptoms: `HoymilesAdaptador._normalizar_inversor()` fixa `energia_total_kwh=0.0` sempre, pois a API `down_module_day_data` não expõe energia total acumulada por microinversor.
- Files: `backend_monitoramento/provedores/hoymiles/adaptador.py:149`
- Trigger: Dashboards Grafana que dependam de `energia_total_kwh` para microinversores Hoymiles mostrarão sempre zero.
- Workaround: Nenhum. A API Hoymiles não expõe esse campo no endpoint atual. Seria necessário um endpoint diferente.

**FusionSolar `status` de usina sempre `'normal'`:**
- Symptoms: `FusionSolarAdaptador._normalizar_usina()` fixa `status='normal'` sem inspecionar os dados da API, pois "FusionSolar não expõe status simples no list" (comentário no código).
- Files: `backend_monitoramento/provedores/fusionsolar/adaptador.py:130`
- Trigger: Dashboards que exibam status de usinas FusionSolar sempre mostrarão "normal", mesmo quando a usina está offline.
- Workaround: O campo `status` é informativo; alertas do próprio provedor detectam falhas independentemente.

---

## Security Considerations

**`SECRET_KEY` tem fallback inseguro:**
- Risk: `SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'changeme-defina-no-env')` — se a variável de ambiente não for definida, o sistema usa uma chave estática pública e conhecida.
- Files: `backend_monitoramento/config/settings/base.py:7`
- Current mitigation: Produção usa `.env` injetado pelo Docker, mas o fallback existe. Se o `.env` falhar por qualquer motivo (permissão, deploy incompleto), o sistema sobe com chave pública.
- Recommendations: Remover o fallback e levantar `ImproperlyConfigured` se a variável estiver ausente. Mesma lógica aplicada a `CHAVE_CRIPTOGRAFIA` (linha 101 — sem fallback, levanta `ValueError` corretamente no uso).

**`CHAVE_CRIPTOGRAFIA` sem fallback mas sem validação de formato Fernet:**
- Risk: Se `CHAVE_CRIPTOGRAFIA` for definida mas inválida (string qualquer, não um token Fernet válido), o erro só explode durante a primeira operação de cripto, não na inicialização do Django.
- Files: `backend_monitoramento/provedores/cripto.py:13-19`
- Current mitigation: `Fernet(chave.encode())` lançará `ValueError` imediatamente se a chave for inválida — mas apenas quando a função for chamada, não no startup.
- Recommendations: Adicionar validação explícita de `CHAVE_CRIPTOGRAFIA` em um `AppConfig.ready()` ou check de deploy.

**Admin Django sem restrição de IP ou 2FA:**
- Risk: O Django admin é o único ponto de controle operacional (credentials, supressão de alertas, destinatários de notificação). Acessível em `/admin/` sem restrição de rede além do `127.0.0.1:8000` do Docker (exposto via reverse proxy).
- Files: `backend_monitoramento/config/settings/base.py`, `backend_monitoramento/config/urls.py`
- Current mitigation: Porta exposta apenas em `127.0.0.1:8000`. Depende do reverse proxy (nginx) para controle de acesso.
- Recommendations: Adicionar `ADMIN_URL` como variável de ambiente para ofuscar a URL do admin. Considerar restrição por IP no nível do Django.

**Senhas Hoymiles trafegam em memória como string limpa:**
- Risk: `self._senha = credenciais['password']` armazena a senha descriptografada em atributo de instância do adaptador durante toda a coleta. Em caso de dump de memória ou log de objeto, a senha é exposta.
- Files: `backend_monitoramento/provedores/hoymiles/adaptador.py:62`
- Current mitigation: Apenas necessária para re-login; a senha nunca é logada diretamente.
- Recommendations: Risco aceitável dado o contexto, mas deve ser documentado explicitamente.

---

## Performance Bottlenecks

**`listar_inversores` Solis faz `time.sleep(0.4)` por inversor sequencialmente:**
- Problem: Em `solis/consultas.py`, para cada inversor, há um `time.sleep(0.4)` + chamada a `/v1/api/inverterDetail`. Com 10 inversores por usina e 5 usinas, isso é 50 chamadas × 0.4s + latência HTTP ≈ 30-40s só para detalhes de inversores.
- Files: `backend_monitoramento/provedores/solis/consultas.py:116-126`
- Cause: Rate limit da Solis (3 req/5s) implementado como sleep bloqueante em thread Celery.
- Improvement path: Paralelizar com `ThreadPoolExecutor` e usar o `LimitadorRequisicoes` (Redis) já disponível, em vez de sleep fixo. Ou implementar batch de detalhe se a Solis suportar.

**FusionSolar tem `time.sleep(5)` fixo entre cada chamada da API:**
- Problem: `_PAUSA_ENTRE_CHAMADAS = 5` segundos é inserido em múltiplos pontos de `fusionsolar/consultas.py` (linhas 117, 159, 198). Uma coleta FusionSolar com 2 tipos de inversor gera: getStationList + getStationRealKpi (5s) + getDevList (5s) + getDevRealKpi×2 (5s+5s) = mínimo 20s de sleep puro.
- Files: `backend_monitoramento/provedores/fusionsolar/consultas.py:32`, `117`, `159`, `198`
- Cause: Rate limit rígido documentado pela Huawei (failCode 407). O sleep é necessário mas bloqueia o worker Celery inteiro.
- Improvement path: Mover a coleta FusionSolar para um worker dedicado com concorrência 1 (`-Q fusionsolar`), liberando os demais workers para outros provedores.

**`LimitadorRequisicoes` usa `time.sleep(ttl + 0.1)` bloqueante:**
- Problem: Quando o rate limit é atingido, o context manager dorme pelo TTL da chave Redis (podendo ser até 60 segundos para Solarman). Isso trava o worker Celery durante todo o sleep.
- Files: `backend_monitoramento/provedores/limitador.py:50-53`
- Cause: Implementação síncrona do rate limiter.
- Improvement path: Em vez de sleep, lançar `ProvedorErroRateLimit` para que a task seja reagendada pelo Beat no próximo ciclo.

**Transação atômica engloba toda a ingestão por credencial:**
- Problem: Em `coletar_dados_provedor`, uma única `transaction.atomic()` envolve upsert de todas as usinas, todos os inversores, e sincronização de alertas. Para contas com muitas usinas/inversores (ex: FusionSolar com 50 usinas, 200 inversores), a transação pode durar dezenas de segundos com muitos locks.
- Files: `backend_monitoramento/coleta/tasks.py:147-158`
- Cause: Design correto para consistência, mas sem divisão por usina.
- Improvement path: Separar em transações por usina (`for dados_usina in dados_usinas: with transaction.atomic(): ...`). Aceita perda parcial por usina, mas elimina lock global.

---

## Fragile Areas

**Parser protobuf Hoymiles manual (`parsear_dados_dia`):**
- Files: `backend_monitoramento/provedores/hoymiles/consultas.py:196-347`
- Why fragile: Decodificação manual de protobuf binário sem schema definido, baseada em engenharia reversa ("Estrutura confirmada com dados reais"). Qualquer mudança na API Hoymiles (campo novo, renumeração de fields, compressão) quebrará silenciosamente ou retornará dados incorretos sem exceção.
- Safe modification: Nunca alterar sem dados de teste reais do endpoint `down_module_day_data`. Qualquer mudança deve ser validada contra dumps binários reais.
- Test coverage: Nenhum teste automatizado cobre o parser protobuf.

**`_BACKENDS_MAP` em `notificacoes/servico.py` é um singleton de módulo mutável:**
- Files: `backend_monitoramento/notificacoes/servico.py:17-25`
- Why fragile: `_BACKENDS_MAP` é um dicionário de módulo preenchido na primeira chamada (`_carregar_backends()`). Em ambiente multi-thread (gunicorn com múltiplos workers), isso é seguro porque cada processo tem seu próprio espaço de memória. Mas em testes, o estado persiste entre testes.
- Safe modification: Testes que envolvam notificações precisam garantir que `_BACKENDS_MAP` não esteja poluído.
- Test coverage: Sem testes de integração para o serviço de notificações.

**Re-login automático em `fusionsolar/consultas.py` dentro de `_post`:**
- Files: `backend_monitoramento/provedores/fusionsolar/consultas.py:51-92`
- Why fragile: A função `_post` faz re-login automático em caso de sessão expirada (401 HTTP ou failCode 305). Isso significa que `_post` pode fazer até 2 chamadas HTTP + 1 re-login por invocação. Erros de re-login são re-classificados como `ProvedorErroAuth` ou `ProvedorErroRateLimit` dependendo do failCode, tornando o fluxo difícil de debugar.
- Safe modification: Qualquer mudança no fluxo de re-login deve ser testada com sessão expirada (forçando failCode 305 manualmente).
- Test coverage: Sem testes automatizados para o fluxo de re-login.

**`sincronizar_alertas` resolve alertas `em_atendimento` de forma inconsistente:**
- Files: `backend_monitoramento/coleta/ingestao.py:282-295`
- Why fragile: O bloco de auto-resolução (`resolvidos = Alerta.objects.filter(estado='ativo')`) exclui apenas `'ativo'` — alertas `'em_atendimento'` que desapareçam do provedor ficam indefinidamente abertos. Isso é intencional ("equipe está ciente"), mas cria alertas zumbis caso a equipe esqueça de fechar manualmente.
- Safe modification: A semântica atual é deliberada. Qualquer mudança deve ser discutida, pois impacta o fluxo operacional de atendimento.
- Test coverage: Sem testes para este cenário específico.

---

## Scaling Limits

**Um único worker Celery com concorrência 2 para todos os provedores:**
- Current capacity: `docker-compose.yml` define `celery worker --concurrency 2`. FusionSolar bloqueia um worker por até 30+ segundos (sleeps + HTTP). Se dois provedores FusionSolar forem configurados, os dois workers ficam ocupados e demais coletas ficam na fila.
- Limit: Com mais de 2 credenciais FusionSolar, o ciclo de 10 minutos não é cumprido.
- Scaling path: Adicionar fila dedicada (`-Q fusionsolar`) com worker isolado e concorrência 1, e fila default para demais provedores.

**`LogColeta` cresce sem limpeza:**
- Current capacity: `LogColeta` não tem política de retenção. A cada 10 minutos, 1 log por provedor é criado. Com 3 provedores e 365 dias: ~216.000 registros/ano.
- Limit: Impacto em queries de admin e na query de verificação de intervalo mínimo em `coletar_dados_provedor`.
- Scaling path: Adicionar task de limpeza de `LogColeta` antigos (>30 dias) similar à `limpar_snapshots_antigos`.

**`payload_bruto` (JSONField) em todos os snapshots e alertas:**
- Current capacity: Cada `SnapshotUsina`, `SnapshotInversor` e `Alerta` armazena o payload completo da API do provedor em `payload_bruto`. Payloads de inversores FusionSolar contêm dezenas de campos KPI.
- Limit: Com 90 dias de retenção, 10 usinas, 50 inversores e coleta a cada 10min: ~3.6M snapshots de inversores. `payload_bruto` pode representar 60-70% do espaço em disco.
- Scaling path: Considerar `payload_bruto=None` por padrão e armazenar apenas quando em modo debug, ou comprimir o JSON antes de salvar.

---

## Dependencies at Risk

**`psycopg2-binary` em produção:**
- Risk: `psycopg2-binary` empacota libpq estaticamente e não é recomendado para produção pelo projeto psycopg (pode conflitar com libpq do sistema).
- Impact: Conectividade com PostgreSQL. Risco baixo em containers isolados, mas pode causar problemas em upgrades de imagem base.
- Migration plan: Substituir por `psycopg2` compilado no Dockerfile ou migrar para `psycopg3` (`psycopg[binary]`).

**`argon2-cffi` como dependência opcional não declarada:**
- Risk: O `_hash_senha_v3` em `hoymiles/autenticacao.py` faz `from argon2.low_level import ...` dentro do bloco `try/except ImportError`, mas `argon2-cffi` não está listado em nenhum `requirements/*.txt`. Se a Hoymiles migrar todos os usuários para v3, a coleta falhará com `ProvedorErro` em produção.
- Impact: Autenticação Hoymiles quebrada para contas v3.
- Migration plan: Adicionar `argon2-cffi` a `requirements/base.txt`.

**`gunicorn` com versão divergente entre dev e prod:**
- Risk: `requirements/dev.txt` não especifica gunicorn (herda `gunicorn==23.*` de `base.txt`), mas `requirements/prod.txt` especifica `gunicorn==22.*`. Há conflito de versão: base.txt pede 23.*, prod.txt pede 22.*.
- Impact: Comportamento diferente entre build de desenvolvimento e produção. O pip resolverá para 22.* em prod.
- Migration plan: Remover `gunicorn` de `requirements/prod.txt` e manter apenas em `base.txt` com a versão correta.

---

## Missing Critical Features

**Sem endpoint de API REST (apenas admin Django):**
- Problem: Não há nenhuma API REST exposta. O único acesso ao sistema é pelo Django admin. Dashboards são servidos via Grafana conectado diretamente ao PostgreSQL. Qualquer integração futura (app mobile, portal web próprio, webhook de terceiros) exigirá criação de API do zero.
- Blocks: Integração com sistemas externos, porta para clientes finais, automação de operações.

**Sem mecanismo de alerta para falha total de coleta:**
- Problem: Se todos os provedores falharem por N ciclos consecutivos (ex: VPS sem internet), não há notificação. O sistema só notifica sobre alertas das usinas, não sobre falhas do próprio sistema de coleta.
- Blocks: Detecção de falha silenciosa na infraestrutura.

**Sem página de status / health check:**
- Problem: Não há endpoint `/health` ou `/status` no Django. O único dado de saúde é a última coleta bem-sucedida no `LogColeta`, visível apenas pelo admin.
- Blocks: Monitoramento externo (uptime robot, Prometheus healthcheck).

---

## Test Coverage Gaps

**Adaptadores de provedores sem testes:**
- What's not tested: `SolisAdaptador`, `HoymilesAdaptador`, `FusionSolarAdaptador` e suas respectivas funções de consulta/autenticação. Toda a camada de integração com APIs externas.
- Files: `backend_monitoramento/provedores/solis/`, `backend_monitoramento/provedores/hoymiles/`, `backend_monitoramento/provedores/fusionsolar/`
- Risk: Mudanças nas APIs externas ou refatorações internas podem quebrar a coleta sem sinalização antes do deploy.
- Priority: High

**`ServicoIngestao` sem testes:**
- What's not tested: Toda a lógica de `sincronizar_alertas()`, upsert de usinas/inversores, lógica de escalonamento de alertas, resolução automática de alertas.
- Files: `backend_monitoramento/coleta/ingestao.py`
- Risk: É o módulo mais crítico do sistema (converte dados externos em registros do banco). Bugs de deduplicação, resolução incorreta de alertas ou duplicidade de notificações não seriam detectados.
- Priority: High

**Tasks Celery sem testes:**
- What's not tested: `coletar_dados_provedor`, `renovar_tokens_provedores`, `limpar_snapshots_antigos`, `enviar_notificacao_alerta`.
- Files: `backend_monitoramento/coleta/tasks.py`, `backend_monitoramento/notificacoes/tasks.py`
- Risk: Falhas de retry, tratamento de auth error, e limpeza de snapshots não testados.
- Priority: Medium

**Parser protobuf Hoymiles sem testes:**
- What's not tested: `parsear_dados_dia()` e funções auxiliares de decodificação (`_decodificar_blob`, `_decodificar_datapoint`, `_decodificar_packed_floats`).
- Files: `backend_monitoramento/provedores/hoymiles/consultas.py:196-347`
- Risk: O parser é implementado por engenharia reversa. Sem testes com fixtures binárias reais, qualquer mudança pode introduzir regressão silenciosa (valores errados, não exceção).
- Priority: High

**`ServicoNotificacao` e backends sem testes:**
- What's not tested: Formatação de mensagens WhatsApp/email, despacho por canal, filtragem por nível, falha isolada de backend.
- Files: `backend_monitoramento/notificacoes/servico.py`, `backend_monitoramento/notificacoes/backends/`
- Risk: Notificações duplicadas ou ausentes não seriam detectadas por testes automáticos.
- Priority: Medium

---

*Concerns audit: 2026-04-07*
