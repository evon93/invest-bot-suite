#!/usr/bin/env python3
"""
tools/render_risk_rules_prod.py

Renders a production risk_rules_prod.yaml by overlaying best parameters from
a JSON config (e.g. frozen topk) onto a base risk_rules.yaml.

Features:
- Validates base YAML structure.
- Applies overlays with dotted-path support or unique-leaf matching.
- Strict validation: fails on ambiguous or unknown keys.
- Adds audit header with SHA256 and commit hash.
- Deterministic output.
"""

import argparse
import hashlib
import json
import subprocess
import sys
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

def get_git_head() -> str:
    """Gets current git HEAD hash, or 'unknown'."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return "unknown"

def compute_sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()

def find_leaf_key_paths(data: Any, target_key: str, current_path: List[str], found_paths: List[List[str]]):
    """Recursively finds all paths to a key in a dictionary."""
    if isinstance(data, dict):
        for k, v in data.items():
            new_path = current_path + [k]
            if k == target_key:
                found_paths.append(new_path)
            find_leaf_key_paths(v, target_key, new_path, found_paths)
    elif isinstance(data, list):
        for i, item in enumerate(data):
            # We don't keys search inside lists for overriding usually, unless strict index logic
            # For this tool, we only override dict keys.
            find_leaf_key_paths(item, target_key, current_path + [str(i)], found_paths)

def set_nested_value(data: Dict, path: List[str], value: Any):
    """Sets a value deeply in a dict using a path list."""
    curr = data
    for i, key in enumerate(path[:-1]):
        if key not in curr:
             # Should verify this logic: usually path exists if we found it or dotted path requires existence
             raise KeyError(f"Path segment '{key}' not found in configuration")
        curr = curr[key]
    curr[path[-1]] = value

def apply_overrides(base_config: Dict, overlay_params: Dict) -> Dict:
    """
    Applies overrides to base_config.
    Returns the modified config (in-place modification is used).
    """
    # Sort keys for deterministic application order
    for key, value in sorted(overlay_params.items()):
        # 1. Handle double underscore as dot
        normalized_key = key.replace("__", ".")
        
        # 2. Check if it is a dotted path
        if "." in normalized_key:
            parts = normalized_key.split(".")
            # Verify path exists
            curr = base_config
            path_exists = True
            for part in parts[:-1]:
                if isinstance(curr, dict) and part in curr:
                    curr = curr[part]
                else:
                    path_exists = False
                    break
            
            if path_exists and isinstance(curr, dict) and parts[-1] in curr:
                curr[parts[-1]] = value
            else:
                 raise ValueError(f"Dotted path '{normalized_key}' does not exist in base configuration.")
        else:
            # 3. Leaf key search
            found_paths = []
            find_leaf_key_paths(base_config, normalized_key, [], found_paths)
            
            # Filter matches to ensure they point to a dict key (not just appearing in a list, though find_leaf logic mainly does dicts)
            # Actually find_leaf recurses lists but 'k' is from dict iteration. So all found_paths end in a dict key.
            
            if len(found_paths) == 0:
                raise ValueError(f"Unknown parameter key: '{key}'. Not found in base configuration.")
            elif len(found_paths) > 1:
                paths_str = [ ".".join(p) for p in found_paths ]
                raise ValueError(f"Ambiguous parameter key: '{key}'. Found at multiple paths: {paths_str}. Use a dotted key (e.g. 'section.{key}') to disambiguate.")
            else:
                # Exact match
                set_nested_value(base_config, found_paths[0], value)
    
    return base_config

def main():
    parser = argparse.ArgumentParser(description="Render production risk rules from overlay")
    parser.add_argument("--base", default="risk_rules.yaml", help="Base YAML configuration")
    parser.add_argument("--overlay", default="configs/best_params_2H.json", help="Overlay JSON (best_params_2H.json)")
    parser.add_argument("--out", default="configs/risk_rules_prod.yaml", help="Output YAML file")

    args = parser.parse_args()
    
    try:
        # Load Base
        base_path = Path(args.base)
        if not base_path.exists():
            raise FileNotFoundError(f"Base file not found: {base_path}")
        
        base_content = base_path.read_bytes()
        base_sha = compute_sha256(base_content)
        base_config = yaml.safe_load(base_content)
        
        # Load Overlay
        overlay_path = Path(args.overlay)
        if not overlay_path.exists():
            raise FileNotFoundError(f"Overlay file not found: {overlay_path}")
            
        overlay_content = overlay_path.read_bytes()
        overlay_sha = compute_sha256(overlay_content)
        overlay_json = json.loads(overlay_content)
        
        # Extract params
        if "selected" in overlay_json and "params" in overlay_json["selected"]:
            overlay_params = overlay_json["selected"]["params"]
        else:
            # Fallback if structure is different (flat?) or error
            # Assuming strictly best_params_2H format
            raise ValueError("Overlay JSON missing 'selected.params' key.")

        # Apply
        final_config = apply_overrides(base_config, overlay_params)
        
        # Metadata
        git_head = get_git_head()
        
        header = (
            f"# PRODUCTION CONFIGURATION\n"
            f"# Generated by tools/render_risk_rules_prod.py\n"
            f"# Base SHA256: {base_sha}\n"
            f"# Overlay SHA256: {overlay_sha}\n"
            f"# Code Commit: {git_head}\n\n"
        )
        
        # Write
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(header)
            # default_flow_style=False ensures expanded block style (readable)
            # sort_keys=False preserves base order if python dict preserves insertion order (Python 3.7+ yes)
            # However, yaml.safe_load might not preserve order unless using specific loader.
            # Standard PyYAML safe_load returns dict, valid for 3.7+ order preservation.
            yaml.dump(final_config, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

        print(f"Rendered production config to: {out_path}")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
