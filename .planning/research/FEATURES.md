# Feature Landscape

**Domain:** Solar inverter monitoring admin panel (internal operations, multi-provider)
**Researched:** 2026-04-07
**Confidence:** MEDIUM-HIGH (patterns verified across SCADA/IoT literature and solar-specific sources)

---

## Table Stakes

Features users expect. Missing = product feels incomplete or forces regression to Grafana.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Plant list with status badges | Core job of the panel: see which usinas have issues at a glance | Low | Badges: normal / degraded / offline / alerting — color-coded |
| Per-plant detail page | Drill down from list to inverters and recent snapshots | Medium | Inverter-level power, status, last-seen timestamp |
| Alert list with state | See open alerts, their severity, and which usina they belong to | Low | State machine: aberto / em_atendimento / resolvido |
| Dashboard summary (KPIs) | Single-screen health overview — replaces Grafana for daily use | Medium | Total active power, # alerts open, # offline plants |
| Warranty status per plant | Core Value per PROJECT.md: "ver quais usinas estão dentro da garantia" | Medium | Valid / expiring-soon (< 90 days) / expired |
| JWT-authenticated login | All routes must be protected; admin-only | Low | simplejwt already chosen |
| Last-collection timestamp | Shows when data was last refreshed; critical with 10-min cycle | Low | Per-plant and global; prevents confusion over stale readings |
| Manual refresh button | User-initiated fetch on demand, independent of poll interval | Low | Required UX when auto-poll cycle is long (10 min) |
| Manufacturer filter on plant list | Solis / Hoymiles / FusionSolar fleet segmentation | Low | Filter + count badge |
| Responsive layout | Accessed from desktop; minimal tablet support acceptable | Low | shadcn/ui handles this by default |

---

## Differentiators

Features that add genuine operational value beyond a basic CRUD panel.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Interactive map of plants (react-leaflet) | Spatial situational awareness — find offline clusters geographically | Medium | Already in scope per PROJECT.md; marker color = status |
| Manufacturer ranking chart | Which provider fleet is performing best; informs procurement decisions | Low | Bar or horizontal bar chart with Recharts |
| Warranty expiry timeline | Visual calendar/gantt of expirations — surfaces upcoming coverage gaps proactively | Medium | 30/60/90-day horizon view; more actionable than a bare date column |
| Alert acknowledgement from panel | Close loop without leaving the panel to use Django admin | Medium | PATCH /alertas/{id}/ with estado transition; needs audit trail |
| Performance degradation indicator | Flag plants whose recent avg power is significantly below historical baseline | High | Requires computing rolling average against capacity; domain-specific logic |
| Data freshness indicator per plant | Distinguish "collecting but degraded" from "offline" from "last collected 2h ago" | Low | Derived from last SnapshotUsina.coletado_em vs. now |
| Bulk warranty assignment | Assign warranty period to multiple plants at once | Low | Useful for fleet commissioning (all plants in a project) |

---

## Anti-Features

Features to deliberately NOT build in this milestone.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Real-time WebSocket push | 10-min collection cycle makes sub-minute latency worthless; adds ASGI migration cost | Polling at 10-min interval with visible "next refresh in Xs" counter |
| Client/end-user portal | PROJECT.md explicitly out of scope; adds auth complexity and multi-tenancy risk | Admin-only panel, no client-facing views |
| Custom chart builder / ad-hoc analysis | Grafana already handles diagnostic analysis; building this duplicates a solved problem | Link to Grafana for deep analysis; keep panel focused on operational decisions |
| Email/WhatsApp notification config from panel | Alert notifications already work via Django admin; duplicating UI in first milestone | Leave notification routing in Django admin until a clear pain point emerges |
| In-panel alert suppression rule editor | Suppression rules are currently managed in Django admin; complex UI for niche need | Keep in Django admin; reference rule IDs in panel read-only if needed |
| Historical time-series chart per inverter | Grafana already does this better; building Recharts time-series for raw snapshots adds scope without proportional value in an admin panel | Link to Grafana for time-series drill-down |
| Mobile app or PWA | Explicitly out of scope per PROJECT.md | N/A this milestone |
| Role-based access control (RBAC) | Single admin user; premature for current scale | Revisit when team grows |
| CSV/PDF report export | High effort, low operational value for real-time panel | If needed later, Django admin already supports basic export |
| Google Maps integration | Decided against: open-source Leaflet is sufficient, zero API cost | Use react-leaflet with OpenStreetMap tiles |

---

## Feature Dependencies

```
JWT Auth
  └── All authenticated endpoints (required for everything)

GarantiaUsina model (backend)
  └── Warranty status badge on plant list
  └── Warranty detail/edit form
  └── Warranty expiry timeline chart
  └── Bulk warranty assignment

SnapshotUsina.coletado_em (exists)
  └── Last-collection timestamp per plant
  └── Data freshness indicator
  └── Staleness detection for polling UI

SnapshotInversor (exists)
  └── Per-plant inverter power readings
  └── Inverter-level status badges
  └── Performance degradation indicator (requires historical baseline)

Alerta model (exists)
  └── Alert list view
  └── Alert state badge
  └── Alert acknowledgement action

Usina.latitude + Usina.longitude (must exist or be added)
  └── Interactive map markers
  └── Spatial filtering
```

---

## MVP Recommendation

Prioritize (ordered by operational value vs. build cost):

1. **JWT auth + plant list with status badges** — enables the panel to exist and be accessed securely
2. **Dashboard summary KPIs** — total power, open alert count, offline plant count — the single-screen health view that replaces Grafana for daily check-ins
3. **Warranty status per plant** — the stated Core Value of the panel; GarantiaUsina model is the prerequisite
4. **Alert list with state** — closes the loop on what Grafana cannot show (alert lifecycle)
5. **Interactive map** — already in PROJECT.md scope; high visual impact relative to code volume (react-leaflet is straightforward)
6. **Manufacturer ranking chart** — low-effort Recharts bar chart, high communication value for fleet health

Defer to subsequent iterations:
- **Performance degradation indicator**: Requires baseline computation logic that adds backend complexity beyond this milestone
- **Warranty expiry timeline (gantt-style)**: Nice to have; date column + badge covers 80% of the value
- **Alert acknowledgement from panel**: Useful but adds write-path complexity; Django admin works for now

---

## UX Pattern Recommendations

### Status Indicators
Use a strict 4-state color system for plants and inverters. Do not invent intermediate states:

| State | Color | Meaning |
|-------|-------|---------|
| normal | green | Collecting data, no active alerts |
| degraded | amber/yellow | Active non-critical alert OR power significantly below capacity |
| offline | red | No snapshot in last 20+ minutes (2+ missed cycles) |
| unknown | gray | Never collected, or GPS missing for map |

The FusionSolar bug (status always 'normal') means the panel **must not** rely on `Usina.status` from the database for the badge. Derive status from: (a) last SnapshotUsina.coletado_em timestamp gap + (b) open Alerta count for the plant. This is resilient to provider API limitations.

### Alert State Display
Follow the existing state machine (aberto / em_atendimento / resolvido):
- `aberto` → red badge
- `em_atendimento` → amber badge with "being handled" semantics — do not auto-resolve these from the panel
- `resolvido` → muted/gray; show in history tab, not in default open-alerts view

Note: The known bug where `em_atendimento` alerts become zombies (CONCERNS.md) means the UI should display the alert age prominently — an `em_atendimento` alert open for 7+ days is likely a zombie and should visually signal that.

### Warranty Presentation
Three visual states are sufficient:

| State | Trigger | Visual |
|-------|---------|--------|
| Valid | expires_at > today + 90 days | green badge "Válida" |
| Expiring soon | today < expires_at <= today + 90 days | amber badge "Vence em N dias" |
| Expired | expires_at <= today | red badge "Vencida" |

A countdown ("Vence em 47 dias") is more actionable than a bare date. The 90-day threshold for "expiring soon" matches standard equipment service-scheduling windows.

On the plant detail page, show a horizontal timeline bar: [start_date -------- today -------- end_date] with a marker at today's position. This conveys how much warranty has elapsed, not just how much remains.

### Polling Strategy
With a 10-minute collection cycle and WSGI-only backend, the correct strategy is:

1. **TanStack Query (`@tanstack/react-query`)** — already implied by the tech stack. Use `refetchInterval: 10 * 60 * 1000` (600000 ms) as the background polling interval.
2. **`staleTime: 9 * 60 * 1000`** (540000 ms) — data is considered fresh for 9 minutes, preventing redundant fetches on tab re-focus during the same cycle.
3. **`refetchOnWindowFocus: true`** — when the user returns to the tab after more than 9 minutes, refetch immediately.
4. **Manual refresh button** — calls `queryClient.invalidateQueries()` on the relevant keys. Essential UX because users returning to the panel after a meeting want fresh data, not to wait up to 10 minutes.
5. **"Next refresh in Xs" counter** — a simple countdown that decrements from 600 to 0, reset on each successful fetch. Prevents the "is this live?" confusion endemic to polling dashboards.
6. **Do NOT poll in background tab continuously** — set `refetchIntervalInBackground: false`. Server load savings outweigh the marginal UX benefit, given the slow data source.

The known TanStack Query v5 issue (#7721 — refetchInterval starts from navigation time, not last fetch time) means the "next refresh in Xs" counter should be driven by the actual `dataUpdatedAt` timestamp from the query result, not a client-side timer started at mount.

### Plant Management Table (Table Stakes UX)
Use shadcn/ui `DataTable` (TanStack Table v8 under the hood). Required capabilities:
- Column sorting (power, status, warranty expiry)
- Text search on plant name and city
- Status filter (multi-select dropdown: normal / degraded / offline)
- Manufacturer filter (Solis / Hoymiles / FusionSolar)
- Pagination (server-side preferred; plants list won't exceed hundreds of rows, so client-side is acceptable)
- Row click → plant detail page
- Bulk select → "Assign warranty" action (deferred to differentiators, but table must support selection from day one)

---

## Known Data Limitations Impacting Features

These backend bugs (from CONCERNS.md) must inform feature design, not be ignored:

| Backend Bug | Feature Impact | Panel Mitigation |
|-------------|---------------|-----------------|
| FusionSolar `status` always 'normal' | Status badge cannot trust `Usina.status` | Derive from `coletado_em` gap + open alerts (see UX Patterns above) |
| Hoymiles `energia_total_kwh` always 0 | Cannot show cumulative energy for Hoymiles plants | Hide or gray-out cumulative energy field for Hoymiles; show "N/A" |
| `nivel_efetivo` always returns `nivel_padrao` | Alert severity display may be misleading | Use the manually-computed effective level from alert payload, not model property |
| Alerts `em_atendimento` can become zombies | Alert list may show perpetually-open items | Show alert age prominently; warn when `em_atendimento` > 72h |

---

## Sources

- ThingsBoard IoT Dashboard patterns: https://thingsboard.io/iot-data-visualization/
- Solar SCADA feature landscape: https://elum-energy.com/solar-scada/ , https://www.greenpowermonitor.com/
- Solar PV KPIs (Performance Ratio, Specific Yield): https://trackso.in/knowledge-base/key-performance-indicators-for-solar-pv-plants/ , https://pv-maps.com/en/blog/solar-performance-ratio-kpi
- TanStack Query polling/stale time: https://tanstack.com/query/v4/docs/framework/react/reference/useQuery , https://tanstack.com/query/v4/docs/framework/react/guides/window-focus-refetching
- shadcn DataTable with bulk actions: https://www.shadcn.io/blocks/tables-bulk-actions , https://www.shadcn.io/ui/data-table
- Monitoring dashboard anti-patterns: https://www.oreilly.com/library/view/practical-monitoring/9781491957349/ch01.html
- Warranty tracking UI patterns: https://www.manageengine.com/products/desktop-central/software-warranty-management.html , https://www.expirationreminder.com/solutions/warranty-tracking-software
- Dashboard UX best practices: https://www.pencilandpaper.io/articles/ux-pattern-analysis-data-dashboards
