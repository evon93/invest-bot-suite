# AG-2J-4-1 Decision Node: Python Version Standardization

**Date**: 2026-01-03
**Ticket**: AG-2J-4-1

## Context

Multiple Python versions (3.12, 3.13) and environments (Windows native vs WSL) create reproducibility friction. Need to establish a "source of truth".

## Audit

- Workflows found:
  - `ci.yml`: `python-version: "3.12"`
  - `edge_tests.yml`: `python-version: '3.12'`
  - `robustness_full.yml`: `python-version: '3.12'`
  - `robustness_quick.yml`: `python-version: '3.12'`
  - `e2e_smoke_2J.yml` (New): `python-version: '3.12'`
- Local Environment: WSL `.venv` is Python 3.12.3.

## Decision

**Python 3.12.x is the canonical runtime.**

- **CI**: All GitHub Actions must use `setup-python` with `python-version: '3.12'`.
- **Local**: Development should primarily occur in WSL (or Linux) with Python 3.12.
- **Windows Native (3.13)**: Not supported as baseline. Users may run it, but CI/Verification implies 3.12 behavior.
- **Housekeeping**: No changes needed in existing workflows as they were already aligned (audit passed).

## Status

IMPLEMENTED. Documented in `registro_de_estado_invest_bot.md` and `.ai/decisions_log.md`.
