# AG-2B-3-3-6 Return Packet — TopK Freeze

## Resultado

✅ Consolidados top-20 candidatos de Full + Strict runs.

## Observaciones

- Ambos runs producen **idénticos** top-20 (mismo seed=42, mismo config_hash)
- Todos los 20 candidatos tienen score=0.993 (empate)
- Diferencias entre candidatos: Kelly cap_factor y DD size_multiplier_soft

## Artefactos Creados

- [2B_3_3_topk_freeze.json](report/2B_3_3_topk_freeze.json) — JSON consolidado
- [2B_3_3_topk_freeze.md](report/2B_3_3_topk_freeze.md) — Resumen con tabla y replay instructions

## Commit

**`e2077e8`** — `report: freeze 2B-3.3 topk candidates`

## Notas

- No hay soporte `--combo-id` en el runner; documentado workaround en freeze.md
