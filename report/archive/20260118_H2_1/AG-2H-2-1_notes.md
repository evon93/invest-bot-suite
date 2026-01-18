# AG-2H-2-1 Design Notes

## Logic

The renderer (`tools/render_risk_rules_prod.py`) enforces strict discipline on configuration overrides:

1. **Unique Leaf**: If a parameter key like `atr_multiplier` exists exactly once in the `risk_rules.yaml` tree, it is overridden automatically.
2. **Dotted Path**: If ambiguity exists or precision is needed, `section.param` syntax targets the exact location.
3. **Double Underscore**: `section__param` is normalized to `section.param` for compatibility with flat JSON environments (like some hyperparameter tuners).

## Validation

- **Ambiguity**: If a key matches >1 leaf, the tool *fails fast* rather than guessing.
- **Safety**: `validate_risk_config.py` is used as a gate in tests to ensure the output is technically valid (schema-wise).

## Audit

The output YAML contains a header with:

- Base file SHA256.
- Overlay file SHA256.
- Git Commit SHA (of the tool code).
This ensures strict provenance for production configurations.
