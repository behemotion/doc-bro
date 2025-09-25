"""
YAML serialization/deserialization utilities.
"""

import yaml
from typing import Any, Dict, Optional
from pathlib import Path
from datetime import datetime


def load_yaml_file(file_path: Path) -> Optional[Dict[str, Any]]:
    """Load YAML file safely."""
    if not file_path.exists():
        return None

    try:
        with open(file_path, 'r') as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        print(f"Error loading YAML from {file_path}: {e}")
        return None


def save_yaml_file(file_path: Path, data: Dict[str, Any]) -> bool:
    """Save data to YAML file."""
    try:
        # Ensure directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, 'w') as f:
            yaml.dump(
                data,
                f,
                default_flow_style=False,
                sort_keys=False,
                allow_unicode=True
            )
        return True
    except Exception as e:
        print(f"Error saving YAML to {file_path}: {e}")
        return False


def merge_yaml_configs(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Merge two YAML configurations, with override taking precedence."""
    result = base.copy()

    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            # Recursive merge for nested dicts
            result[key] = merge_yaml_configs(result[key], value)
        else:
            # Direct override
            result[key] = value

    return result


def datetime_representer(dumper, data):
    """Custom YAML representer for datetime objects."""
    return dumper.represent_scalar('tag:yaml.org,2002:str', data.isoformat())


def datetime_constructor(loader, node):
    """Custom YAML constructor for datetime strings."""
    value = loader.construct_scalar(node)
    return datetime.fromisoformat(value)


# Register custom handlers
yaml.add_representer(datetime, datetime_representer)
yaml.add_constructor('tag:yaml.org,2002:str', datetime_constructor)


def validate_yaml_structure(data: Dict[str, Any], required_keys: list) -> tuple[bool, list[str]]:
    """Validate YAML structure has required keys."""
    errors = []

    for key in required_keys:
        if key not in data:
            errors.append(f"Missing required key: {key}")

    return len(errors) == 0, errors


def create_backup(file_path: Path, suffix: Optional[str] = None) -> Optional[Path]:
    """Create a backup of a YAML file."""
    if not file_path.exists():
        return None

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    suffix = suffix or f"backup.{timestamp}"
    backup_path = file_path.with_suffix(f".yaml.{suffix}")

    try:
        import shutil
        shutil.copy2(file_path, backup_path)
        return backup_path
    except Exception as e:
        print(f"Error creating backup: {e}")
        return None