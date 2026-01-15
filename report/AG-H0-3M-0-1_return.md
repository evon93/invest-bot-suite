# AG-H0-3M-0-1 Return Packet

## Ticket Summary

- **ID**: AG-H0-3M-0-1
- **Parent**: main@5620a1d
- **Status**: ✅ PASS

## Changes Made

Normalized 4 report artifacts from UTF-16 (PowerShell default) to UTF-8:

| File | Before | After |
|------|--------|-------|
| AG-3M-1-1_last_commit.txt | 146 bytes (UTF-16) | 71 bytes (UTF-8) |
| AG-3M-1-1_diff.patch | 22456 bytes | 37782 bytes (full patch) |
| AG-3M-2-1_last_commit.txt | 120 bytes (UTF-16) | 58 bytes (UTF-8) |
| AG-3M-2-1_diff.patch | 15772 bytes | 38735 bytes (full patch) |

## Verification

```bash
# Content verification
cat report/AG-3M-1-1_last_commit.txt
c957bc3 3M.1: adapter-mode end-to-end via ExchangeAdapter (paper/stub)

cat report/AG-3M-2-1_last_commit.txt
5620a1d 3M.2: adapter-mode checkpoint/resume determinista
```

## Commands Used

```bash
# Via WSL for proper UTF-8 encoding
wsl bash -c "git show -s --oneline c957bc3 > report/AG-3M-1-1_last_commit.txt"
wsl bash -c "git show -s --oneline 5620a1d > report/AG-3M-2-1_last_commit.txt"
wsl bash -c "git show --patch c957bc3 > report/AG-3M-1-1_diff.patch"
wsl bash -c "git show --patch 5620a1d > report/AG-3M-2-1_diff.patch"
```
