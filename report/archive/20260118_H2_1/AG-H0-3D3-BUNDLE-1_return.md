# AG-H0-3D3-BUNDLE-1 Return Packet

## Resumen

Bundle creado con archivos canónicos de 3D.3 para adjuntar a IAs externas.

## Bundle

- **Archivo**: `report/inputs_3D3_bundle.zip`
- **Manifest**: `report/inputs_3D3_manifest.md`

## Contenido

### Source Files (7)

| Archivo | Path Original |
|---------|---------------|
| `loop_stepper.py` | `engine/loop_stepper.py` |
| `bus_workers.py` | `engine/bus_workers.py` |
| `position_store_sqlite.py` | `state/position_store_sqlite.py` |
| `events_v1.py` | `contracts/events_v1.py` |
| `inmemory_bus.py` | `bus/inmemory_bus.py` |
| `bus_base.py` | `bus/bus_base.py` |
| `test_stepper_bus_mode_3D.py` | `tests/test_stepper_bus_mode_3D.py` |

### Diff Patches (3)

| Patch | Ticket |
|-------|--------|
| `AG-3D-1-1_diff.patch` | Risk rules fail-fast |
| `AG-3D-2-1_diff.patch` | In-memory bus abstraction |
| `AG-3D-3-1_diff.patch` | Bridge adapters + bus mode |

## Git Reference

- **Branch**: `feature/3C_7_close`
- **HEAD**: `47876c95c07fb7d909bc72b7d745e82bb6eed7fd`

## Total: 10 archivos incluidos
