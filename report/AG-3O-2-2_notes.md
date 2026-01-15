# AG-3O-2-2 Notes: Cleanup Details

## Cleanup Action

As part of AG-3O-2-2, ephemeral files in `report/` that were accidentally tracked in the previous iteration were removed from the git index (but remain on disk unless cleaned by `cleanup_report.py`).

## Untracked Patterns

Files matching the H0.1 `.gitignore` rules in `report/` were untracked:

- `report/git_status_*.txt`
- `report/head_*.txt`
- `report/pytest_*.txt` (snapshots/logs)
- `report/run_log.txt`
- `report/ls_*.txt`
- `report/python_*.txt`
- `report/working_tree_diff_*.txt`

## Kept (Tier-1)

Only the following were explicitly retained in the index:

- `report/AG-*.md` (Return Packets)
- `report/AG-*.patch` (Diffs)
- `report/HOUSEKEEPING_report_policy.md`
- `report/session_*.md` (Session logs if relevant)
- `report/*_handoff_*.md`

This aligns with the `HOUSEKEEPING_report_policy.md` (Tier 1 vs Tier 2).
