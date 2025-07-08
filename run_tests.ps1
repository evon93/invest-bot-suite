# run_tests.ps1 — Sitúa + Testea invest-bot-suite

# 1️⃣ Navegar a la carpeta del proyecto
Set-Location "$HOME\Desktop\invest-bot-suite"

# 2️⃣ Verificar archivos clave
if (-not (Test-Path .\risk_manager_v0_4.py)) {
    Write-Error "Falta el SHIM: risk_manager_v0_4.py"
    exit 1
}
if (-not (Test-Path .\risk_manager_v_0_4.py)) {
    Write-Error "Falta el módulo real: risk_manager_v_0_4.py"
    exit 1
}

# 3️⃣ Instalar dependencias mínimas
pip install pyyaml pytest --disable-pip-version-check

# 4️⃣ Ejecutar pytest
pytest -q
