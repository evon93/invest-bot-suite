# AG-3F-4-3: Actualizar Checkpoint Durante el Loop — Return Packet

**Ticket**: AG-3F-4-3  
**Rama**: `feature/3F_4_crash_recovery_v0`  
**Fecha**: 2026-01-07

---

## Resumen

El checkpoint.json ahora se actualiza de forma atómica durante el loop, habilitando resume real.

### Archivos Modificados

| Archivo | Cambio |
|---------|--------|
| [engine/loop_stepper.py](file:///c:/Users/ivn_b/Desktop/invest-bot-suite/engine/loop_stepper.py#L343-L470) | +checkpoint/checkpoint_path/start_idx params, +actualización tras cada bar |
| [tools/run_live_3E.py](file:///c:/Users/ivn_b/Desktop/invest-bot-suite/tools/run_live_3E.py#L195-L220) | +pasa checkpoint/checkpoint_path/start_idx a run_bus_mode |

---

## Dónde se Actualiza el Checkpoint

**Función**: `LoopStepper.run_bus_mode()` en `engine/loop_stepper.py`

**Líneas**: ~465-468 (tras cada iteración del loop Phase 1)

```python
# Update checkpoint after processing this bar index
if checkpoint and checkpoint_path:
    checkpoint = checkpoint.update(i - warmup)  # idx relative to warmup
    checkpoint.save_atomic(checkpoint_path)
```

---

## Campo Cursor

- **Campo**: `last_processed_idx`
- **Tipo**: Índice relativo al warmup (0-indexed)
- **Motivo**: El loop bus mode itera sobre `range(warmup, end_idx)`. El índice `i - warmup` representa la posición relativa dentro del rango procesable.

---

## Evidencia: Checkpoint Avanza

**Antes** (AG-3F-4-2):

```json
{"last_processed_idx": -1, "processed_count": 0}
```

**Después** (AG-3F-4-3):

```json
{
  "run_id": "run_42_10",
  "last_processed_idx": 9,
  "processed_count": 10,
  "updated_at": "2026-01-07T19:11:26.479822+00:00"
}
```

---

## Resume Real

Con `--resume`:

1. Carga checkpoint existente
2. Calcula `start_idx = checkpoint.last_processed_idx + 1`
3. `run_bus_mode` inicia en `warmup + start_idx`
4. No reprocesa items anteriores

---

## Comandos Ejecutados

| Comando | Resultado |
|---------|-----------|
| `python tools/run_live_3E.py --run-dir ... --max-steps 10` | checkpoint: `last_processed_idx=9` |
| `pytest -q` | **432 passed**, 10 skipped |

---

## DoD Verificado

- [x] checkpoint.json se actualiza durante el loop (no se queda en -1)
- [x] `--resume` reanuda desde el punto correcto
- [x] `pytest -q` PASS

---

## Artefactos

- `report/pytest_3F4_checkpoint_test.txt`
- `report/AG-3F-4-3_pytest.txt`
- `report/AG-3F-4-3_diff.patch`
- `report/AG-3F-4-3_return.md` (este archivo)
