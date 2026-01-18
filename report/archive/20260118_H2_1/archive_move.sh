#!/bin/bash
cd /mnt/c/Users/ivn_b/Desktop/invest-bot-suite

# Listar archivos untracked en report/ (no en archive/, no AG-H2-1-1)
git ls-files --others --exclude-standard -- report/ | grep -v 'report/archive/' | grep -v 'AG-H2-1-1' | while read f; do
    basename=$(basename "$f")
    mv "$f" "report/archive/20260118_H2_1/$basename"
done

echo "Archivos movidos: $(ls report/archive/20260118_H2_1/ | wc -l)"
