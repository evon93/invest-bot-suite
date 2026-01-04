# AG-H0-AUDITPACK-1 Return Packet — IA Audit Packs

**Fecha:** 2026-01-04  
**Ticket:** AG-H0-AUDITPACK-1  
**Estado:** ✅ COMPLETADO

---

## 1. Estructura Creada

```
report/external_ai/packs/3C_3_risk_v0_6/
├── grok4/
│   ├── manifest.md          # Instrucciones + enfoque (arquitectura, edge cases)
│   ├── payload.md           # Snippets clave + test matrix
│   └── txt/                  # 11 archivos .txt
├── gemini3pro/
│   ├── manifest.md          # Enfoque (serialización, invariantes)
│   ├── payload.md           # Snippets clave + preguntas
│   └── txt/                  # 11 archivos .txt
└── deepseek/
    ├── manifest.md          # Enfoque (lógica, paridad)
    ├── payload.md           # Snippets clave + tabla paridad
    └── txt/                  # 11 archivos .txt
```

---

## 2. Archivos Convertidos a .txt

| Archivo Original | Destino (.txt) |
|------------------|----------------|
| contracts/events_v1.py | events_v1.py.txt |
| adapters/risk_input_adapter.py | risk_input_adapter.py.txt |
| risk_manager_v0_6.py | risk_manager_v0_6.py.txt |
| risk_manager_v_0_4.py | risk_manager_v_0_4.py.txt |
| tools/run_live_integration_3B.py | run_live_integration_3B.py.txt |
| configs/risk_rules_prod.yaml | risk_rules_prod.yaml.txt |
| report/AG-3C-3-1_diff.patch | AG-3C-3-1_diff.patch.txt |
| tests/test_risk_manager_v0_6_contract.py | test_*.py.txt |
| tests/test_risk_manager_v0_6_compat_v0_4_parity.py | test_*.py.txt |
| tests/test_contracts_events_v1_roundtrip.py | test_*.py.txt |
| tests/test_risk_input_adapter.py | test_*.py.txt |

---

## 3. Enfoque por IA

| IA | Enfoque | Preguntas clave |
|----|---------|-----------------|
| **Grok4** | Arquitectura + Edge cases + Test matrix | Missing scenarios, short positions |
| **Gemini3Pro** | Serialización + Invariantes + <=30 líneas | Type coercion, roundtrip symmetry |
| **DeepSeek** | Lógica + Paridad v0.4/v0.6 | Parity issues, additional tests |

---

## 4. Uso de Packs

**Opción A: File Upload**

1. Subir archivos de `txt/` (renombrar .txt si necesario)
2. Pegar manifest.md para contexto

**Opción B: Copy-Paste**

1. Copiar contenido de `payload.md` directamente al chat

---

## 5. Commit

```
2794e1f chore: add external audit packs for 3C.3
```

---

## 6. Artefactos

- [AG-H0-AUDITPACK-1_diff.patch](AG-H0-AUDITPACK-1_diff.patch)
- [AG-H0-AUDITPACK-1_last_commit.txt](AG-H0-AUDITPACK-1_last_commit.txt)
