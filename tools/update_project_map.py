#!/usr/bin/env python
# update_project_map.py — Antigravity workflow helper
# Genera un mapa avanzado del repo en .ai/project_map.md

from __future__ import annotations

from pathlib import Path
import datetime as dt
import subprocess
from typing import Dict, List, Tuple


ROOT = Path(__file__).resolve().parents[1]
AI_DIR = ROOT / ".ai"
OUTPUT_PATH = AI_DIR / "project_map.md"

IGNORE_DIRS = {
    ".git",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    ".idea",
    ".vscode",
    ".mypy_cache",
    ".ruff_cache",
    ".DS_Store",
}

IGNORE_FILE_SUFFIXES = {
    ".pyc",
    ".pyo",
    ".log",
}

CORE_PATTERNS = (
    "strategy_engine",
    "risk_manager",
    "risk_context",
    "backtest",
    "stress",
)


def get_current_branch() -> str:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=str(ROOT),
            text=True,
        )
        return out.strip()
    except Exception:
        return "unknown"


def iter_repo_files() -> List[Path]:
    files: List[Path] = []
    for item in ROOT.iterdir():
        if item.is_file():
            if item.suffix in IGNORE_FILE_SUFFIXES:
                continue
            files.append(item)
        elif item.is_dir():
            if item.name in IGNORE_DIRS:
                continue
            if item.name.startswith(".") and item.name != ".ai":
                continue
            for sub in item.rglob("*"):
                if sub.is_dir():
                    continue
                if sub.suffix in IGNORE_FILE_SUFFIXES:
                    continue
                if any(p.name in IGNORE_DIRS for p in sub.parents):
                    continue
                files.append(sub)
    return files


def collect_files_by_top_level(files: List[Path]) -> Dict[str, List[Path]]:
    mapping: Dict[str, List[Path]] = {}
    for abs_path in files:
        rel = abs_path.relative_to(ROOT)
        parts = rel.parts
        if len(parts) == 1:
            key = "root"
        else:
            key = parts[0]
        mapping.setdefault(key, []).append(rel)
    for key in mapping:
        mapping[key] = sorted(mapping[key], key=lambda p: str(p))
    return mapping


def compute_stats(files: List[Path]) -> Tuple[int, int, Dict[str, Dict[str, int]]]:
    total_py = 0
    total_tests = 0
    by_top: Dict[str, Dict[str, int]] = {}
    for abs_path in files:
        rel = abs_path.relative_to(ROOT)
        parts = rel.parts
        top = "root" if len(parts) == 1 else parts[0]
        stats = by_top.setdefault(top, {"py": 0, "tests": 0})
        if rel.suffix == ".py":
            total_py += 1
            stats["py"] += 1
            if "tests" in parts or rel.name.startswith("test_"):
                total_tests += 1
                stats["tests"] += 1
        elif "tests" in parts and rel.name.startswith("test_"):
            total_tests += 1
            stats["tests"] += 1
    return total_py, total_tests, by_top


def detect_core_modules(files: List[Path]) -> List[Path]:
    core: List[Path] = []
    for abs_path in files:
        rel = abs_path.relative_to(ROOT)
        name = rel.name
        if not name.endswith(".py"):
            continue
        for pat in CORE_PATTERNS:
            if pat in name:
                core.append(rel)
                break
    core = sorted(set(core), key=lambda p: str(p))
    return core


def render_markdown(
    mapping: Dict[str, List[Path]],
    total_py: int,
    total_tests: int,
    stats_by_top: Dict[str, Dict[str, int]],
    core_modules: List[Path],
) -> str:
    now = dt.datetime.now().astimezone()
    branch = get_current_branch()
    lines: List[str] = []
    lines.append("# Project Map — invest-bot-suite")
    lines.append("")
    lines.append(f"- Generado: {now.isoformat(timespec='seconds')}")
    lines.append(f"- Rama git: {branch}")
    lines.append("")
    lines.append("Este archivo se genera automáticamente con `tools/update_project_map.py`.")
    lines.append("No editar manualmente salvo para notas puntuales.")
    lines.append("")
    lines.append("## Visión general")
    lines.append("")
    lines.append(f"- Archivos Python totales: {total_py}")
    lines.append(f"- Tests detectados: {total_tests}")
    lines.append("")
    if core_modules:
        lines.append("## Módulos core detectados")
        lines.append("")
        for rel in core_modules:
            lines.append(f"- `{rel}`")
        lines.append("")
    HOT_PY_THRESHOLD = 20
    HOT_TEST_THRESHOLD = 10
    hotspots: List[str] = []
    for top, stats in sorted(stats_by_top.items()):
        if stats["py"] >= HOT_PY_THRESHOLD or stats["tests"] >= HOT_TEST_THRESHOLD:
            hotspots.append(
                f"- `{top}/`: {stats['py']} .py, {stats['tests']} tests"
            )
    if hotspots:
        lines.append("## Hotspots (alta densidad de código/tests)")
        lines.append("")
        lines.extend(hotspots)
        lines.append("")
    root_files = mapping.get("root", [])
    if root_files:
        lines.append("## Archivos en la raíz del repo")
        lines.append("")
        for rel in root_files:
            lines.append(f"- `{rel}`")
        lines.append("")
    for key in sorted(mapping.keys()):
        if key == "root":
            continue
        lines.append(f"## Directorio: {key}/")
        lines.append("")
        files = mapping[key]
        for rel in files:
            lines.append(f"- `{rel}`")
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    AI_DIR.mkdir(parents=True, exist_ok=True)
    files = iter_repo_files()
    mapping = collect_files_by_top_level(files)
    total_py, total_tests, stats_by_top = compute_stats(files)
    core_modules = detect_core_modules(files)
    md = render_markdown(mapping, total_py, total_tests, stats_by_top, core_modules)
    OUTPUT_PATH.write_text(md, encoding="utf-8")


if __name__ == "__main__":
    main()
