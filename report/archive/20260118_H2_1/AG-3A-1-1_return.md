# AG-3A-1-1 Event-Driven Contracts V1

## Veredicto

- **Estado**: IMPLEMENTED
- **Location**: `contracts/event_messages.py`
- **Tests**: `tests/test_contracts_3A.py` (Passed in Pytest suite)
- **Docs**: Updated Bridge + Register (typo fixes)

## Entregables

1. **Contracts**: `OrderIntent`, `RiskDecision`, `ExecutionReport`, `ExecutionContext` implementados como dataclasses.
    - Soportan `to_json` / `from_json` canónicos.
    - Validan campos requeridos (`symbol`, `side`, `ref_order_event_id`, etc).
2. **Tests**: Roundtrip verificada. Compatibility (extra fields) verificada.
3. **Docs Fixes**:
    - `bridge_2J_to_3A_report.md`: Head updated to `0bf352c`.
    - `registro_de_estado_invest_bot.md`: Typo `ools` -> `tools` fixed.

## Artefactos

- `report/AG-3A-1-1_diff.patch`
- `report/AG-3A-1-1_pytest.txt`
- `report/AG-3A-1-1_run_git.txt`
- `report/AG-3A-1-1_last_commit.txt`

## Próximos Pasos (3A)

- Integrar estos contratos en la lógica de bucle en vivo (wiring).
