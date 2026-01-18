# AG-H0-WSL-EXEC-0-6 Ejecución WSL

## Veredicto

- **WSL + Venv**: OK (Python 3.12.3, pip 25.3)
- **Smoke Tests**: OK (189 passed, 6 skipped in ~103s)
- **Observaciones**: Warnings de runtime en `divide_base_impl.py` (pandas/numpy). No bloqueante para ejecución smoke.

## Plantilla Comando Reutilizable

```bash
wsl -e bash -lc "cd /mnt/c/Users/ivn_b/Desktop/invest-bot-suite && source .venv/bin/activate && <CMD>"
```

Ejemplos:

- `wsl -e bash -lc "cd /mnt/c/Users/ivn_b/Desktop/invest-bot-suite && source .venv/bin/activate && pytest -q"`
- `wsl -e bash -lc "cd /mnt/c/Users/ivn_b/Desktop/invest-bot-suite && source .venv/bin/activate && python tools/run_calibration_2B.py --mode quick"`
