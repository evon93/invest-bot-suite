#!/bin/bash
set -e
echo "[Codex] Boot invest-bot-suite"

#-- Actualiza instalador
pip install --upgrade pip wheel

#-- Dependencias runtime (Gemini ↑)
pip install numpy==1.28.* pandas==2.2.* pyyaml==6.0.* \
           aiokafka==0.10.* "redis[hiredis]==5.0.*" orjson==3.10.*

#-- Herramientas de desarrollo / CI
pip install -U pytest black ruff pytest-benchmark asv

#-- Carpeta de datos (controlada por VARIABLE $DATA_DIR)
mkdir -p "${DATA_DIR:-/workspace/data}"
echo "Codex listo: $(date)" > "${DATA_DIR:-/workspace/data}/codex_boot.log"
