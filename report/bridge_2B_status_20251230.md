# Bridge — 2B status (2025-12-30)

## Resumen
- Cerrado: 'calibration grid no discrimina' (ahora discrimina métricas y no solo config hash).
- 2E gate ya estaba integrado y verificado en main (run_meta.json + results.csv con activity/rejection fields).
- 2B runner añade --scenario sensitivity para runs deterministas que activan guardrails.

## Evidencia clave
- report/AG-2B-3-3-7_return.md + report/out_2B_3_3_grid_sensitivity_20251230_202500/
- report/AG-2B-3-3-8_return.md + report/out_2B_3_3_grid_discriminates_20251230/

## Métricas discriminantes (2B sensitivity)
- score: 0.274 vs 0.346
- pct_time_hard_stop: 0.714 vs 0.571
- 24 combos / 24 hashes únicos

## Próximo foco sugerido
- Definir cómo se consume el 'topk.json' (freeze/promote) para la siguiente fase.
