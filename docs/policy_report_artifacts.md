# Report Artifact Storage Policy

**Ticket**: AG-H1-1-1  
**Status**: Active

---

## Overview

This policy defines what files in `report/` should be tracked in git vs uploaded as CI artifacts.

## Categories

### Category A: Track in Git

Essential documentation for reproducibility and audit trail:

| Pattern | Description |
|---------|-------------|
| `AG-*_return.md` | Return packets (required) |
| `AG-*_last_commit.txt` | Commit references |
| `AG-*_notes.md` | Decision notes |
| `bridge_*_report.md` | Phase bridge reports |
| `ORCH_HANDOFF_*.md` | Orchestrator handoffs |

### Category B: CI Artifacts Only

Large/ephemeral files uploaded to GitHub Actions artifacts:

| Pattern | Description |
|---------|-------------|
| `AG-*_diff.patch` | Full diffs (can be large) |
| `AG-*_run.txt` | Run/execution logs |
| `pytest_*.txt` | Test output logs |
| `runs/**` | CI run directories |
| `out_*/**` | Output directories |

## Size Thresholds

| Level | Size | Action |
|-------|------|--------|
| OK | < 1 MB | Allowed |
| Warning | 1-5 MB | Review required |
| Block | > 5 MB | Must use CI artifacts |

## Tools

### Validation

```bash
# Check policy
python tools/report_artifact_policy.py --check

# Generate digest for large file
python tools/report_artifact_policy.py --digest report/large_file.txt
```

### Cleanup

```bash
# Preview ephemeral files
python tools/cleanup_report.py --dry-run

# Delete ephemeral files older than 7 days
python tools/cleanup_report.py --apply --days 7
```

## CI Integration

Workflows use `actions/upload-artifact@v4` for large outputs:

```yaml
- name: Upload Run Artifacts
  uses: actions/upload-artifact@v4
  with:
    name: run-artifacts
    path: ${{ env.ARTIFACT_DIR }}
```

## Implementation

- `.gitignore` patterns enforce Category B exclusions
- `report_artifact_policy.py` validates at CI time
- Large files should include SHA256 digest in return packet
