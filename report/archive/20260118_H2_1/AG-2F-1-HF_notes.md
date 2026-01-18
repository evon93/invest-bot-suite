# AG-2F-1-HF Design Notes

## Decision: Option A

Chose Option A (return_stats parameter) over Option B (separate function) because:

1. **Single entry point**: One function to maintain, test, document
2. **Keyword-only**: `return_stats` is keyword-only (`*,`) to prevent positional mistakes
3. **Default False**: Backward compatible - existing callers get DataFrame
4. **Union return type**: Modern Python supports `-> DataFrame | Tuple[DataFrame, LoadStats]`

## Why not Option B?

- Two functions = duplicated logic or wrapper overhead
- More surface area for documentation
- Callers need to know which to use

## Breaking change scope

- Only callers that were explicitly unpacking `df, stats = load_ohlcv(...)`
  (which didn't exist before the previous commit) need `return_stats=True`
