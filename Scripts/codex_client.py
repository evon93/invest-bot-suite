"""
codex_client.py
Wrapper mínimo para lanzar jobs al entorno Codex desde GitHub Actions
"""

from __future__ import annotations
import os, json, openai, sys

# --- configuración ---------------------------------------------------------
ENV_ID = os.getenv("CODEX_ENV_ID")          # se inyecta desde GitHub Secrets
API_KEY = os.getenv("OPENAI_API_KEY")       # idem

if not ENV_ID or not API_KEY:
    sys.exit("❌  Falta CODEX_ENV_ID u OPENAI_API_KEY en variables de entorno")

openai.api_key = API_KEY

# --- API de conveniencia ----------------------------------------------------
def run(code: str, timeout: int = 180) -> dict[str, str]:
    """
    Ejecuta `code` (Python) en el entorno Codex y devuelve:
    {stdout, stderr, exit_code}
    """
    response = openai.ChatCompletion.create(
        environment=ENV_ID,
        model="o3",                       # Kai
        tools=[{"type": "code_interpreter"}],
        messages=[{"role": "user", "content": code}],
        temperature=0,
        max_tokens=1024,
        timeout=timeout,
    )
    tool_args = response.choices[0].message.tool_calls[0].args
    return json.loads(tool_args)

# CLI rápido:  `python scripts/codex_client.py "print(2+2)"`
if __name__ == "__main__":
    user_code = sys.argv[1] if len(sys.argv) > 1 else "print('Hello Codex')"
    result = run(user_code)
    print("STDOUT:\n", result.get("stdout", ""))
    print("STDERR:\n", result.get("stderr", ""))
    print("Exit code:", result.get("exit_code"))
