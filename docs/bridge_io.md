# Bridge I/O Documentation

## Overview

`tools/bridge_headers.sh` generates reproducible SESSION and DELTA markdown files for Orchestrator handoffs. This eliminates manual header creation and ensures consistent environment snapshots.

## Usage

```bash
bash tools/bridge_headers.sh [TAG]
```

- **TAG**: Optional identifier (default: `MANUAL`)
- **Output**: `report/SESSION_<TAG>.md` and `report/DELTA_<TAG>.md`

## Example

```bash
# Generate headers for a new phase
bash tools/bridge_headers.sh H3T

# View generated files
cat report/SESSION_H3T.md
cat report/DELTA_H3T.md
```

## Captured Information

| Field | Source |
|-------|--------|
| `timestamp` | `date -Iseconds` |
| `repo_path` | Script directory parent |
| `os` | WSL detection + `/etc/os-release PRETTY_NAME` |
| `git_branch` | `git branch --show-current` |
| `git_head` | `git rev-parse HEAD` |
| `git_status` | `git status --porcelain` (clean/dirty summary) |
| `python_system` | `python3 --version` |
| `venv_exists` | `.venv/` directory check |
| `python_venv` | `.venv/bin/python --version` (if exists) |
| `pytest_last` | Most recent `report/pytest_*.txt` last line |

## Requirements

- Bash (POSIX-ish)
- Git
- Python 3 (for version detection)

## Notes

- Run from repo root or any subdirectory
- Creates `report/` directory if missing
- No external dependencies required
