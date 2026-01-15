# AG-2E-3-3-3 Return Packet — FAIL-path Evidence

## Objetivo

Generar evidencia determinista donde el Activity Gate **FALLE** y `--strict-gate` devuelva exit code 1.

## Resultado

✅ **Evidencia generada exitosamente sin cambios de código.**

## Smokes Ejecutados

| Run | Comando | Exit Code | Gate Status | Reason |
|-----|---------|-----------|-------------|--------|
| 1 | `--mode full --max-combinations 1` | 0 | FAIL | `active_n_below_min` |
| 2 | `--mode full --max-combinations 1 --strict-gate` | **1** | FAIL | `active_n_below_min` |

## Verificación en `run_meta.json`

Ambos archivos contienen:

- `"gate_passed": false`
- `"insufficient_activity": true`
- `"gate_fail_reasons": ["active_n_below_min"]`
- `"suggested_exit_code": 1`
- `"git_head": "e3fb90d3087b"`

## Artefactos

1. [run_meta.json (normal)](report/out_2E_3_3_fail_smoke/run_meta.json)
2. [run_meta.json (strict)](report/out_2E_3_3_fail_strict_smoke/run_meta.json)
3. [AG-2E-3-3-3_run.txt](report/AG-2E-3-3-3_run.txt)
4. [AG-2E-3-3-3_last_commit.txt](report/AG-2E-3-3-3_last_commit.txt)

## HEAD Final

`e3fb90d` (2E: enforce activity gate thresholds + granular fail reasons)

## Notas

- No se requirieron cambios de código. El threshold `min_active_n` del profile `full_demo` es suficientemente alto para fallar con solo 1 combo.
- No se generó `AG-2E-3-3-3_diff.patch` porque no hubo cambios.
