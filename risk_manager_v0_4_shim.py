"""
risk_manager_v0_4_shim.py - SHIM universal mejorado
===================================================
Resuelve imports para todas las variantes de nombres posibles.
Compatible con duplicados de Windows y diferentes convenciones.
"""

from __future__ import annotations

import sys
import os
from pathlib import Path
from importlib.util import spec_from_file_location, module_from_spec
from typing import Optional, Any

_cached_module = None

def _find_real_module() -> Optional[Path]:
    """Busca el archivo de implementación real con variantes de nombres."""
    candidates = [
        "risk_manager_v0_4.py",    # Nombre preferido
        "risk_manager_v_0_4.py",    # Nombre alternativo
    ]
    
    current_dir = Path(__file__).parent
    
    for candidate in candidates:
        path = current_dir / candidate
        if path.exists():
            return path
    
    # Si no se encuentra, intenta resolver en el directorio padre
    parent_dir = current_dir.parent
    for candidate in candidates:
        path = parent_dir / candidate
        if path.exists():
            return path
    
    return None

def _load_module() -> Any:
    """Carga dinámicamente el módulo real."""
    global _cached_module
    if _cached_module is not None:
        return _cached_module

    module_path = _find_real_module()
    if not module_path:
        raise ImportError("No se encontró el módulo risk_manager")

    module_name = module_path.stem
    spec = spec_from_file_location(module_name, module_path)
    
    if not spec or not spec.loader:
        raise ImportError(f"No se pudo cargar {module_path}")
    
    module = module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    _cached_module = module
    return module

# Reexportar la clase RiskManager
try:
    RiskManager = _load_module().RiskManager
except ImportError as e:
    raise ImportError(f"Error al cargar RiskManager: {e}") from e