# Phase 2: REST Endpoints — Discussion Log

**Session:** 2026-04-08
**Áreas discutidas:** 3 (Organização da app `api`, Estratégia de filtros, Paginação do histórico de snapshots)

---

## Área 1: Organização da app `api`

| Pergunta | Opções apresentadas | Resposta |
|----------|-------------------|----------|
| Como organizar views e serializers? | Pacote por domínio / Arquivo único views.py | **Pacote por domínio** |
| Como registrar rotas dos ViewSets? | Router central único / urls.py por domínio | **Router central único** |

---

## Área 2: Estratégia de filtros

| Pergunta | Opções apresentadas | Resposta |
|----------|-------------------|----------|
| Como implementar filtros? | django-filter / get_queryset() manual | **django-filter** |
| Valores do campo `status_garantia`? | ativa/vencida/sem_garantia / ativa/inativa | **ativa/vencida/sem_garantia (seguir USN-04)** |
| Parâmetro em /api/garantias/? | `filtro=ativas/vencendo/vencidas` / renomear para `status` | **Manter `filtro=ativas/vencendo/vencidas`** |

---

## Área 3: Paginação do histórico de snapshots

| Pergunta | Opções apresentadas | Resposta |
|----------|-------------------|----------|
| Comportamento padrão de snapshots? | Offset 100/pág / Cursor 100/pág / Sem paginação com limite | **Paginação por offset, 100/pág** |
| Paginação global dos endpoints? | Manter padrão atual / Verificar e ajustar | **Verificar e ajustar se necessário** |

---

*Gerado por /gsd-discuss-phase em 2026-04-08*
