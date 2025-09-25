"""
XDG-compliant directory utilities for DocBro settings.
"""

import os
from pathlib import Path
from typing import Optional

def get_xdg_config_home() -> Path:
    """Get XDG config home directory."""
    xdg_config = os.environ.get('XDG_CONFIG_HOME')
    if xdg_config:
        return Path(xdg_config)
    return Path.home() / '.config'

def get_xdg_data_home() -> Path:
    """Get XDG data home directory."""
    xdg_data = os.environ.get('XDG_DATA_HOME')
    if xdg_data:
        return Path(xdg_data)
    return Path.home() / '.local' / 'share'

def get_xdg_cache_home() -> Path:
    """Get XDG cache home directory."""
    xdg_cache = os.environ.get('XDG_CACHE_HOME')
    if xdg_cache:
        return Path(xdg_cache)
    return Path.home() / '.cache'

def get_docbro_config_dir() -> Path:
    """Get DocBro configuration directory."""
    config_dir = get_xdg_config_home() / 'docbro'
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir

def get_docbro_data_dir() -> Path:
    """Get DocBro data directory."""
    data_dir = get_xdg_data_home() / 'docbro'
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir

def get_docbro_cache_dir() -> Path:
    """Get DocBro cache directory."""
    cache_dir = get_xdg_cache_home() / 'docbro'
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir

def get_global_settings_path() -> Path:
    """Get path to global settings file."""
    return get_docbro_config_dir() / 'settings.yaml'

def get_project_settings_path(project_dir: Optional[Path] = None) -> Path:
    """Get path to project settings file."""
    if project_dir is None:
        project_dir = Path.cwd()
    return project_dir / '.docbro' / 'settings.yaml'

def ensure_directory(path: Path) -> None:
    """Ensure a directory exists."""
    path.mkdir(parents=True, exist_ok=True)

def expand_path(path: str) -> Path:
    """Expand user home directory and resolve path."""
    return Path(path).expanduser().resolve()