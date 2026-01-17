# Bridge Report: H1 → Next Phase

## Fase Completada: H1 (Operabilidad Post-3O)

### Done ✅

- Artifact storage policy implementada y documentada
- Exit code semantics en run_live_3E.py (0=shutdown, 2=error)
- Tests de SIGTERM/SIGINT en adapter-mode con checkpoint
- CI gate workflow para validar H1

### Open / Pendiente

- Return packets históricos untracked (~200 archivos)
- Deprecation warnings de pandas (7)
- Validación exit codes en supervisor no extendida

---

## Próximos Tickets Sugeridos

| ID | Descripción | Prioridad |
|----|-------------|-----------|
| H2-1 | Cleanup/commit batch de return packets históricos | H1 |
| H2-2 | Migrar `is_datetime64tz_dtype` a nueva API pandas | H2 |
| H2-3 | Extender exit code validation a supervisor | H2 |
| H2-4 | Consolidar workflows CI (H1 + 3O + smoke) | H2 |
| H2-5 | Documentar flujo de creación de tickets en .agent/ | H3 |

---

## Riesgos Técnicos

| Riesgo | Impacto | Mitigación |
|--------|---------|------------|
| Crecimiento report/ | Repo bloat | Policy ya implementada + cleanup tool |
| Pandas deprecations | Tests warnings | Ticket H2-2 prioritario |
| Untracked files noise | Git status ruido | Commit selectivo o gitignore |

---

## Archivos Clave para Siguiente Fase

- `tools/report_artifact_policy.py` — Validación de artifacts
- `docs/policy_report_artifacts.md` — Documentación policy
- `.github/workflows/h1_gate.yml` — CI gate H1
- `registro_de_estado_invest_bot.md` — Estado del proyecto
