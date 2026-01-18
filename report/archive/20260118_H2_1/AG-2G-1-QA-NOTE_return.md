# AG-2G-1-QA-NOTE Return Packet

## Result

✅ Documentation updated.

## Summary

Updated `report/AG-2G-1-QA_notes.md` to correctly describe the implementation of Spearman correlation:

- **Before**: `corr(method='spearman')` (implied SciPy dependency).
- **After**: `corr(method='pearson')` on ranks (SciPy-free equivalent).

## Commit

**`HEAD`** — `docs: fix QA notes spearman explanation`

## Files Changed

`report/AG-2G-1-QA_notes.md`
