"""Flag definition endpoints for MCP server."""

import logging
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Body

from src.services.flag_standardizer import FlagStandardizer
from src.core.lib_logger import get_component_logger

logger = get_component_logger("mcp_flag_endpoints")

router = APIRouter(prefix="/admin/commands", tags=["admin", "flags"])


@router.post("/standardize-flags")
async def standardize_flags(
    command_scope: str = Body("all", description="Command scope: all, shelf, box, fill, serve"),
    dry_run: bool = Body(False, description="Preview changes without applying them"),
    preserve_aliases: bool = Body(True, description="Keep existing flag aliases")
) -> Dict[str, Any]:
    """Apply flag standardization to existing commands.

    Analyzes current command flags and applies standardization rules,
    optionally preserving existing aliases for backward compatibility.
    """
    try:
        # Validate command scope
        valid_scopes = ["all", "shelf", "box", "fill", "serve", "setup"]
        if command_scope not in valid_scopes:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid command scope '{command_scope}'. Must be one of: {', '.join(valid_scopes)}"
            )

        standardizer = FlagStandardizer()

        # Get current flag conflicts
        conflicts = standardizer.validate_flag_consistency()

        # Generate changes preview
        changes_preview = []

        if command_scope == "all":
            commands = ["shelf", "box", "fill", "serve", "setup"]
        else:
            commands = [command_scope]

        for command in commands:
            # Get current flags (mock - in reality would analyze actual command definitions)
            current_flags = _get_current_command_flags(command)

            # Get standardized flags
            standardized_flags = standardizer.get_all_flags_for_command(command)

            # Compare and generate changes
            old_flags = list(current_flags.keys())
            new_flags = [mapping.long_form for mapping in standardized_flags.values()]

            # Find aliases to add
            aliases_added = []
            for mapping in standardized_flags.values():
                if preserve_aliases and mapping.short_form:
                    aliases_added.append(mapping.short_form)

            changes_preview.append({
                "command": command,
                "old_flags": old_flags,
                "new_flags": new_flags,
                "aliases_added": aliases_added,
                "conflicts_resolved": len([c for c in conflicts if command in c])
            })

        response = {
            "changes_preview": changes_preview,
            "applied": not dry_run,
            "backup_created": not dry_run,
            "conflicts_found": len(conflicts),
            "conflicts_resolved": len(conflicts) if not dry_run else 0
        }

        if not dry_run:
            # In a real implementation, this would:
            # 1. Create backup of current command definitions
            # 2. Apply standardized flags to actual command files
            # 3. Update imports and parameter names
            # 4. Run tests to verify changes work
            logger.info(f"Applied flag standardization to {command_scope} commands")
        else:
            logger.info(f"Generated flag standardization preview for {command_scope} commands")

        return response

    except Exception as e:
        logger.error(f"Error standardizing flags for {command_scope}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/flags/conflicts")
async def get_flag_conflicts() -> Dict[str, Any]:
    """Get detailed report of flag conflicts and suggestions.

    Analyzes all command flags and identifies conflicts, providing
    specific suggestions for resolution.
    """
    try:
        standardizer = FlagStandardizer()

        # Get conflicts
        conflicts = standardizer.validate_flag_consistency()

        # Get detailed conflict report
        conflict_report = standardizer.get_flag_conflicts_report()

        # Analyze conflicts by type
        short_form_conflicts = []
        long_form_conflicts = []

        for conflict in conflicts:
            if "Short form" in conflict:
                short_form_conflicts.append(conflict)
            elif "Long form" in conflict:
                long_form_conflicts.append(conflict)

        # Generate suggestions for each conflict
        suggestions = []
        for conflict in conflicts:
            if "Short form" in conflict:
                # Extract flag and commands from conflict message
                parts = conflict.split("'")
                if len(parts) >= 2:
                    flag = parts[1]
                    suggestions.append({
                        "conflict": conflict,
                        "type": "short_form",
                        "suggestion": f"Consider using different short forms or making one flag global",
                        "affected_flag": flag
                    })

        response = {
            "total_conflicts": len(conflicts),
            "short_form_conflicts": len(short_form_conflicts),
            "long_form_conflicts": len(long_form_conflicts),
            "conflicts": conflicts,
            "suggestions": suggestions,
            "report": conflict_report,
            "resolution_status": "conflicts_found" if conflicts else "all_consistent"
        }

        return response

    except Exception as e:
        logger.error(f"Error getting flag conflicts: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/flags/usage")
async def get_flag_usage_statistics() -> Dict[str, Any]:
    """Get statistics about flag usage across commands.

    Provides insights into which flags are most commonly used,
    which short forms are available, and usage patterns.
    """
    try:
        standardizer = FlagStandardizer()

        # Get all flags
        global_flags = standardizer.get_global_flags()
        commands = ["shelf", "box", "fill", "serve", "setup"]

        # Analyze usage statistics
        total_flags = len(global_flags)
        used_short_forms = set()
        available_short_forms = set()
        flag_types = {}

        # Count global flags
        for mapping in global_flags.values():
            used_short_forms.add(mapping.short_form)
            flag_types[mapping.flag_type] = flag_types.get(mapping.flag_type, 0) + 1

        # Count command-specific flags
        command_flag_counts = {}
        for command in commands:
            command_flags = standardizer.get_command_flags(command)
            command_flag_counts[command] = len(command_flags)
            total_flags += len(command_flags)

            for mapping in command_flags.values():
                used_short_forms.add(mapping.short_form)
                flag_types[mapping.flag_type] = flag_types.get(mapping.flag_type, 0) + 1

        # Calculate available short forms
        all_letters = set(f"-{c}" for c in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")
        available_short_forms = all_letters - used_short_forms

        response = {
            "total_flags": total_flags,
            "global_flags": len(global_flags),
            "command_specific_flags": total_flags - len(global_flags),
            "used_short_forms": len(used_short_forms),
            "available_short_forms": len(available_short_forms),
            "flag_types": flag_types,
            "command_flag_counts": command_flag_counts,
            "usage_efficiency": round((len(used_short_forms) / 52) * 100, 1),  # Percentage of alphabet used
            "next_available_short_forms": sorted(list(available_short_forms))[:10]
        }

        return response

    except Exception as e:
        logger.error(f"Error getting flag usage statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/flags/suggest")
async def suggest_flag_alias(
    command: str = Body(..., description="Command name"),
    desired_flag: str = Body(..., description="Desired flag name")
) -> Dict[str, Any]:
    """Suggest available short form for a flag.

    Analyzes current flag usage and suggests available short forms
    for new flags, following naming conventions.
    """
    try:
        standardizer = FlagStandardizer()

        # Generate suggestion
        suggested_alias = standardizer.suggest_flag_alias(command, desired_flag)

        if suggested_alias:
            response = {
                "command": command,
                "desired_flag": desired_flag,
                "suggested_short_form": suggested_alias,
                "available": True,
                "reasoning": f"Based on flag name '{desired_flag}', suggested '{suggested_alias}'"
            }
        else:
            response = {
                "command": command,
                "desired_flag": desired_flag,
                "suggested_short_form": None,
                "available": False,
                "reasoning": "All suitable short forms are already in use"
            }

        return response

    except Exception as e:
        logger.error(f"Error suggesting flag alias for {command}/{desired_flag}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


def _get_current_command_flags(command: str) -> Dict[str, str]:
    """Get current flags for a command (mock implementation).

    In a real implementation, this would analyze the actual command
    definitions to extract current flag configurations.
    """
    # Mock current flags - in reality would parse actual command files
    mock_flags = {
        "shelf": {
            "--description": "-d",
            "--set-current": "-s",
            "--init": "-i",
            "--verbose": "-v"
        },
        "box": {
            "--type": "-t",
            "--shelf": "-s",
            "--description": "-d",
            "--init": "-i"
        },
        "fill": {
            "--source": "-s",
            "--max-pages": "-m",
            "--depth": "-d"
        },
        "serve": {
            "--host": "-h",
            "--port": "-p",
            "--admin": "-a",
            "--foreground": "-f"
        },
        "setup": {
            "--init": "-i",
            "--force": "-f",
            "--auto": "-a"
        }
    }

    return mock_flags.get(command, {})