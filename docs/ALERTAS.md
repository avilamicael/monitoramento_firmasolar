# Mapeamento de Alertas — Firma Solar

> Documento de referência para entender os alertas recebidos dos provedores, como são salvos no banco e como priorizar os problemas.

---

## 1. Visão Geral do Fluxo

```
Celery Beat (a cada 10 min)
       │
       ▼
API do Provedor (Solis / FusionSolar / Hoymiles)
       │
       ▼
Normalização → DadosAlerta (dataclass intermediária)
       │
       ▼
ServicoIngestao.sincronizar_alertas()
  ├─ Verifica CatalogoAlarme (cria automaticamente se tipo novo)
  ├─ Verifica RegraSupressao (global ou por usina)
  ├─ Se suprimido → descarta silenciosamente
  └─ Upsert no modelo Alerta (cria ou atualiza)
       │
       ▼
ServicoNotificacao
  ├─ Email (SMTP)
  └─ WhatsApp (Meta Cloud API ou Evolution API)
```

---

## 2. Dados Recebidos dos Provedores vs Banco de Dados

### 2.1 Solis Cloud

**Endpoint:** `POST /v1/api/alarmList`

| Campo da API Solis | Tipo | Campo no Banco (`Alerta`) | Observação |
|---|---|---|---|
| `id` | string | `id_alerta_provedor` | Chave de deduplicação |
| `alarmCode` | string | `catalogo_alarme.id_alarme_provedor` | Lookup no catálogo |
| `stationId` | string | `usina` (FK) | Busca por `id_usina_provedor` |
| `alarmMsg` | string | `mensagem` | Descrição do alarme |
| `alarmLevel` | string | `nivel` | `"1"` → `critico`, `"3"` → `aviso` |
| `alarmBeginTime` | int (ms) | `inicio` | Convertido de timestamp em ms |
| `alarmDeviceSn` ou `sn` | string | `equipamento_sn` | SN do equipamento afetado |
| `state` | string | `estado` (implícito) | `"0"` → ativo; outros → resolvido |
| `advice` | string | `sugestao` | Sugestão de reparo |
| *(resposta completa)* | JSON | `payload_bruto` | Auditoria |

**Mapeamento de níveis:**

| Solis `alarmLevel` | Nível no Sistema |
|---|---|
| `"1"` | `critico` |
| `"3"` | `aviso` |
| outros | `info` (fallback) |

---

### 2.2 FusionSolar

**Endpoint:** `/thirdData/getAlertList`

| Campo da API FusionSolar | Tipo | Campo no Banco (`Alerta`) | Observação |
|---|---|---|---|
| `alarmId` | int | `catalogo_alarme.id_alarme_provedor` | ID do tipo de alarme |
| `alarmId` + `devSn` | — | `id_alerta_provedor` | Combinado: `"alarmId_devSn"` |
| `stationCode` | string | `usina` (FK) | Busca por `id_usina_provedor` |
| `alarmName` | string | `mensagem` | Nome do alarme |
| `alarmLevel` | int | `nivel` | Ver tabela abaixo |
| `devSn` | string | `equipamento_sn` | SN do dispositivo |
| `repairSuggestion` | string | `sugestao` | Sugestão de reparo |
| *(não fornece)* | — | `inicio` | Preenchido com `now()` na coleta |
| *(não fornece)* | — | `estado` | Sempre `ativo` (resolução por desaparecimento) |
| *(resposta completa)* | JSON | `payload_bruto` | Auditoria |

**Mapeamento de níveis:**

| FusionSolar `alarmLevel` | Nível no Sistema |
|---|---|
| `1` | `critico` |
| `2` | `importante` |
| `3` | `aviso` |
| `4` | `info` |

> **Atenção:** FusionSolar não retorna data de início nem estado de resolução.
> A resolução é detectada quando o alerta **desaparece** da resposta da API na próxima coleta.

---

### 2.3 Hoymiles S-Cloud

> **Diferença importante:** Hoymiles **não tem endpoint de alertas dedicado**.
> Os alertas são derivados de flags booleanas (`warn_data`) dentro dos dados de cada usina.

| Flag em `warn_data` | Mensagem gerada | Nível |
|---|---|---|
| `g_warn` | Aviso de rede elétrica (grid) | `aviso` |
| `l3_warn` | Aviso de isolamento L3 | `aviso` |
| `s_ustable` | Tensão instável | `aviso` |
| `s_uoff` | Sistema desligado | `critico` |
| `dl` | Desconexão de link/comunicação | `critico` |
| `s_uid` | Falha de identificação do dispositivo | `aviso` |

| Campo derivado | Campo no Banco (`Alerta`) | Observação |
|---|---|---|
| `"{plant_id}_{flag}"` | `id_alerta_provedor` | Ex: `"12345_s_uoff"` |
| `plant_id` | `usina` (FK) | — |
| Mensagem do dicionário | `mensagem` | Traduzida no código |
| Nível do dicionário | `nivel` | Fixo por tipo de flag |
| `now()` | `inicio` | Hoymiles não rastreia horários |
| *(vazio)* | `equipamento_sn` | Sem rastreio por dispositivo |
| *(vazio)* | `sugestao` | Não fornecido pela API |
| Dados da usina | `payload_bruto` | Auditoria |

---

## 3. Schema do Banco de Dados

### Tabela: `alertas_alerta`

| Campo | Tipo | Descrição |
|---|---|---|
| `id` | UUID (PK) | Identificador único |
| `usina_id` | UUID (FK) | Qual usina tem o alerta |
| `catalogo_alarme_id` | int (FK, nullable) | Tipo do alarme no catálogo |
| `id_alerta_provedor` | string (max 200) | ID externo do provedor (deduplicação) |
| `equipamento_sn` | string (max 100) | Serial do equipamento afetado |
| `mensagem` | text | Descrição do problema |
| `nivel` | string | `info`, `aviso`, `importante`, `critico` |
| `inicio` | datetime | Quando o alerta começou |
| `fim` | datetime (nullable) | Quando foi resolvido |
| `estado` | string | `ativo`, `em_atendimento`, `resolvido` |
| `sugestao` | text | Sugestão de reparo |
| `anotacoes` | text | Anotações da equipe |
| `notificacao_enviada` | bool | Se notificação já foi disparada |
| `payload_bruto` | JSON | Resposta bruta do provedor |
| `criado_em` | datetime | — |
| `atualizado_em` | datetime | — |

**Restrição única:** `(usina_id, id_alerta_provedor)`

---

### Tabela: `alertas_catalogoalarme`

Catálogo de tipos de alarmes. Criado automaticamente quando um tipo novo aparece.

| Campo | Tipo | Descrição |
|---|---|---|
| `id` | int (PK) | — |
| `provedor` | string | `solis`, `hoymiles`, `fusionsolar` |
| `id_alarme_provedor` | string | ID externo do tipo de alarme |
| `nome_pt` | string | Nome em português (editável) |
| `nome_original` | string | Nome original do provedor |
| `tipo` | string | Categoria (editável) |
| `nivel_padrao` | string | Nível padrão do tipo |
| `nivel_sobrescrito` | bool | Se `True`, operador fixou o nível manualmente |
| `suprimido` | bool | Se `True`, nunca gera alerta em nenhuma usina |
| `sugestao` | text | Sugestão padrão de reparo |
| `criado_auto` | bool | `True` = criado automaticamente (novo tipo desconhecido) |

---

### Tabela: `alertas_regrasupressao`

Regras para silenciar um tipo de alarme temporária ou permanentemente.

| Campo | Tipo | Descrição |
|---|---|---|
| `catalogo_id` | int (FK) | Qual tipo de alarme suprimir |
| `escopo` | string | `todas` (todas usinas) ou `usina` (usina específica) |
| `usina_id` | UUID (FK, nullable) | Obrigatório se `escopo='usina'` |
| `motivo` | text | Motivo da supressão |
| `ativo_ate` | datetime (nullable) | `null` = permanente; data = expira automaticamente |

---

## 4. Tipos de Alertas e Categorias de Problema

As categorias são preenchidas automaticamente no `CatalogoAlarme` quando um tipo de alarme é detectado pela primeira vez. O operador pode corrigir via Admin → Catálogo de Alarmes.

**Valores possíveis do campo `tipo`:**

| Valor no banco | Descrição |
|---|---|
| `equipamento` | Falha em hardware (inversor, string, módulo) |
| `comunicacao` | Perda de comunicação / conectividade |
| `rede_eletrica` | Instabilidade na rede elétrica (grid) |
| `sistema_desligado` | Usina completamente parada |
| `preventivo` | Informativo, manutenção, sem urgência — **fallback quando nenhuma regra se aplica** |

### Lógica de inferência automática

**Hoymiles** — mapeamento direto por flag (determinístico):

| Flag | Categoria inferida |
|---|---|
| `g_warn` | `rede_eletrica` |
| `l3_warn` | `rede_eletrica` |
| `s_ustable` | `rede_eletrica` |
| `s_uoff` | `sistema_desligado` |
| `dl` | `comunicacao` |
| `s_uid` | `comunicacao` |

**Solis e FusionSolar** — matching por palavras-chave no nome do alarme, avaliado em ordem de prioridade:

1. `sistema_desligado` — desligado, shutdown, parado, stopped
2. `comunicacao` — comunicação, communication, desconex, disconnect, datalogger, link, offline, network
3. `rede_eletrica` — grid, tensão, voltage, frequency, frequência, isolamento, isolation, l3
4. `equipamento` — inversor, inverter, string, módulo, module, device, falha, failure, erro, temperatura, overtemperature
5. `preventivo` — fallback (nenhuma palavra-chave encontrada)

> **Nota:** o matching é heurístico. Alarmes ambíguos (ex: "inverter offline" pode ser equipamento ou comunicação) serão categorizados pelo critério de prioridade e devem ser revisados manualmente pelo operador no primeiro mês de uso.

---

### Categoria `equipamento`

Problemas físicos no hardware (inversores, strings, módulos).

| Fonte | Indicadores |
|---|---|
| Solis | `alarmLevel=1`, alarmes com código de erro de inversor |
| FusionSolar | `alarmLevel=1` ou `2`, `alarmName` contendo "inverter", "device", "string" |
| Hoymiles | `s_uid` (falha de identificação do dispositivo) |

**Gravidade:** `critico` ou `importante`
**Impacto:** Redução ou parada de geração
**Ação:** Técnico no local

---

### Categoria `comunicacao`

Falha de comunicação entre os equipamentos e a nuvem do provedor.

| Fonte | Indicadores |
|---|---|
| Hoymiles | `dl` (Desconexão de link/comunicação) |
| Hoymiles | `s_uid` (pode indicar problema de comunicação) |
| Solis | Alarmes com `alarmCode` relacionado a datalogger/comunicação |
| FusionSolar | `alarmName` contendo "communication", "offline", "network" |

**Gravidade:** `critico` ou `aviso`
**Impacto:** Sem visibilidade do sistema (pode mascarar outros problemas)
**Ação:** Verificar internet/roteador na usina antes de despachar técnico

---

### Categoria `rede_eletrica`

Problemas relacionados à qualidade ou continuidade da rede elétrica.

| Fonte | Indicadores |
|---|---|
| Hoymiles | `g_warn` (Aviso de rede elétrica) |
| Hoymiles | `l3_warn` (Aviso de isolamento L3) |
| Hoymiles | `s_ustable` (Tensão instável) |
| FusionSolar | `alarmLevel=3`, `alarmName` com "grid", "voltage", "frequency" |
| Solis | `alarmLevel=3`, alarmes de qualidade de rede |

**Gravidade:** `aviso`
**Impacto:** Inversores podem desligar temporariamente
**Ação:** Monitorar; se persistir, acionar concessionária

---

### Categoria `sistema_desligado`

A usina está completamente offline / sem geração.

| Fonte | Indicadores |
|---|---|
| Hoymiles | `s_uoff` (Sistema desligado) |
| Solis | Estado `state='0'` combinado com alarme de alto nível |
| FusionSolar | Alerta de `alarmLevel=1` com "shutdown" ou "offline" |

**Gravidade:** `critico`
**Impacto:** Zero geração
**Ação:** Verificar alimentação da usina, checar CB/disjuntores

---

### Categoria `preventivo`

Avisos de manutenção preventiva, atualizações ou condições não urgentes. Também é o valor padrão quando nenhuma regra de categorização se aplica.

| Fonte | Indicadores |
|---|---|
| FusionSolar | `alarmLevel=4` (`info`) |
| Solis | Alarmes de manutenção programada |

**Gravidade:** `info`
**Impacto:** Nenhum imediato
**Ação:** Agendar revisão preventiva

---

## 5. Priorização Sugerida

| Prioridade | Nível | Categoria | Tempo de Resposta Sugerido |
|---|---|---|---|
| P1 | `critico` | D — Sistema desligado | Imediato (< 1h) |
| P1 | `critico` | A — Equipamento crítico | Imediato (< 1h) |
| P2 | `critico` | B — Comunicação perdida | Até 4h (verificar se é falso positivo) |
| P3 | `importante` | A — Equipamento degradado | Até 24h |
| P4 | `aviso` | C — Rede elétrica instável | Monitorar; acionar se persistir > 2h |
| P4 | `aviso` | B — Comunicação intermitente | Monitorar |
| P5 | `info` | E — Preventivo | Agendar revisão |

---

## 6. Ciclo de Vida de um Alerta

```
[Provedor retorna alerta]
       │
       ▼
   estado: ATIVO
   task Celery agenda notificação (após commit da transação)
       │
       ├─── Equipe reconhece
       │         ▼
       │    estado: EM_ATENDIMENTO
       │    (coleta nunca sobrescreve este estado)
       │
       └─── Alerta some da API do provedor
                 ▼
            estado: RESOLVIDO  (somente se estava ATIVO)
            fim: (timestamp automático)
            ──────────────────────────────────────────
            ⚠️  Se estava EM_ATENDIMENTO: NÃO é alterado
               (ver item "Futuro — Resolução automática de em_atendimento")
```

> **Reabertura:** Se um alerta resolvido reaparece na API do provedor,
> o estado volta para `ativo` automaticamente.

---

## 7. Arquivos de Referência no Código

| Arquivo | Responsabilidade |
|---|---|
| `alertas/models.py` | Modelos: `Alerta`, `CatalogoAlarme`, `RegraSupressao` |
| `alertas/categorizacao.py` | Inferência automática de categoria para o catálogo |
| `coleta/ingestao.py` | Lógica principal: `ServicoIngestao.sincronizar_alertas()` |
| `coleta/tasks.py` | Tarefa Celery de coleta a cada 10 min |
| `provedores/solis/adaptador.py` | Normalização Solis → `DadosAlerta` |
| `provedores/fusionsolar/adaptador.py` | Normalização FusionSolar → `DadosAlerta` |
| `provedores/hoymiles/adaptador.py` | Extração de flags + normalização Hoymiles → `DadosAlerta` |
| `notificacoes/servico.py` | Despacho de notificações por canal e nível |
| `notificacoes/tasks.py` | Task Celery assíncrona de envio de notificação |
| `notificacoes/backends/email.py` | Backend SMTP |
| `notificacoes/backends/whatsapp.py` | Backend WhatsApp (Meta ou Evolution) |

---

## 8. Limitações Conhecidas dos Provedores

Estas limitações são impostas pelas APIs e não têm solução imediata no lado do sistema:

1. **Hoymiles — sem data de início:** `inicio` é sempre preenchido com a hora da coleta, não com a hora real do problema. Dificulta calcular a duração real do incidente.

2. **FusionSolar — sem data de início:** Mesma limitação. O `inicio` reflete a primeira coleta que detectou o alerta.

3. **Hoymiles — sem serial de equipamento:** Alertas são por usina, não por dispositivo. Não é possível identificar qual inversor específico está com problema.

4. **FusionSolar e Hoymiles — resolução por desaparecimento:** Nenhum dos dois sinaliza resolução diretamente. O sistema detecta que o alerta "sumiu" na próxima coleta (janela de até 10 min). Isso é aceitável para o ciclo de 10 minutos atual.

---

## 9. Itens Implementados

### Categorização automática do catálogo de alarmes
- **Arquivo:** `alertas/categorizacao.py`
- **Quando:** ao criar uma entrada no `CatalogoAlarme` pela primeira vez
- **Como:** mapeamento direto para Hoymiles (flags conhecidas); matching por palavras-chave para Solis e FusionSolar
- **Override:** operador pode corrigir via Admin → Catálogo de Alarmes → campo "tipo"

### Notificações assíncronas via Celery
- **Arquivo:** `notificacoes/tasks.py`
- **Task:** `enviar_notificacao_alerta(alerta_id, motivo)`
- **Como:** a task é agendada com `transaction.on_commit()` — só é despachada após o commit da transação de coleta
- **Benefício:** falha no envio (SMTP, WhatsApp) não afeta a coleta nem reverte a transação; retenta automaticamente até 3x com intervalo de 60s

---

## 10. Itens Planejados para o Futuro

> Estes itens precisam de discussão com o dono do sistema antes de implementação.

### Regras de notificação por persistência
Hoje qualquer alerta novo dispara notificação imediatamente. A ideia é adicionar lógica de filtragem antes de notificar, por exemplo:
- Só notificar se o alerta persistir por mais de N coletas consecutivas sem resolução
- Só notificar em determinados horários (ex: não notificar `aviso` à madrugada)
- Silenciar automaticamente alertas que aparecem e somem com frequência (oscilação normal de rede)

**Decisões necessárias:** definir o N mínimo de coletas por categoria; definir janelas de silêncio por nível; definir o que conta como "intermitente" vs problema real.

### Resolução automática de alertas `em_atendimento`
Atualmente, quando um alerta está com `estado=em_atendimento` e a próxima coleta detecta que o problema desapareceu do provedor, o sistema **não altera o estado** nem notifica a equipe.

O comportamento desejado no futuro:
- Detectar que o problema sumiu do provedor mesmo que o estado seja `em_atendimento`
- Notificar a equipe: "O sistema identificou que o problema foi resolvido automaticamente na última coleta. Confirme o encerramento do atendimento."
- **Não** alterar o estado automaticamente — a equipe decide se fecha o chamado

**Cuidado:** nem todo tipo de problema pode ter essa regra. Alertas de rede elétrica oscilam com frequência — uma ausência numa coleta não significa resolução definitiva. A implementação deve levar em conta a categoria do alarme.

**Decisões necessárias:** quais categorias permitem resolução automática; quantas coletas consecutivas sem o alerta para confirmar resolução; como apresentar a notificação diferenciando de um alerta novo.

### Alertas baseados em métricas de geração
Os alertas atuais vêm exclusivamente das APIs dos provedores. Não existe lógica interna que detecte anomalias de produção, como:
- Usina gerando abaixo do esperado para a irradiância do dia
- Queda brusca de geração sem alerta associado no provedor
- Inversor com produção significativamente abaixo dos demais da mesma usina

**Decisões necessárias:** definir baseline de geração esperada por usina/período; definir thresholds de desvio que justificam alerta; definir fonte de dados de irradiância (API de clima externa ou estimativa histórica).
