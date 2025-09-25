"""
UI models for interactive settings menu.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SettingsMenuItem(BaseModel):
    """Individual menu item for settings interface."""

    key: str = Field(..., description="Setting key/field name")
    display_name: str = Field(..., description="Human-readable name")
    value: Any = Field(..., description="Current value")
    value_type: str = Field(..., description="Data type (int/float/str/bool)")
    description: str = Field(..., description="Help text")
    is_editable: bool = Field(default=True, description="Can be modified")
    validation: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Validation rules (min/max/choices)"
    )

    def format_value(self) -> str:
        """Format value for display."""
        if self.value_type == "bool":
            return "Yes" if self.value else "No"
        elif self.value_type == "float":
            return f"{self.value:.2f}"
        elif self.key == "rate_limit":
            return f"{self.value:.1f} req/s"
        elif self.key == "timeout":
            return f"{self.value} seconds"
        else:
            return str(self.value)

    def get_type_hint(self) -> str:
        """Get type hint for display."""
        if not self.is_editable:
            return f"{self.value_type} (fixed)"

        if self.validation:
            if "min" in self.validation and "max" in self.validation:
                return f"{self.value_type} ({self.validation['min']}-{self.validation['max']})"
            elif "choices" in self.validation:
                return f"{self.value_type} (choice)"

        return self.value_type


class MenuState(BaseModel):
    """State management for interactive settings menu."""

    current_index: int = Field(default=0, description="Selected item index")
    items: List[SettingsMenuItem] = Field(
        default_factory=list,
        description="Menu items"
    )
    editing: bool = Field(default=False, description="Currently editing a value")
    edit_buffer: str = Field(default="", description="Text being edited")
    message: Optional[str] = Field(None, description="Status/error message")
    changes_made: bool = Field(default=False, description="Track if any changes made")

    def move_up(self) -> bool:
        """Move selection up."""
        if self.current_index > 0:
            self.current_index -= 1
            return True
        return False

    def move_down(self) -> bool:
        """Move selection down."""
        if self.current_index < len(self.items) - 1:
            self.current_index += 1
            return True
        return False

    def get_current_item(self) -> Optional[SettingsMenuItem]:
        """Get currently selected item."""
        if 0 <= self.current_index < len(self.items):
            return self.items[self.current_index]
        return None

    def start_editing(self) -> bool:
        """Start editing current item."""
        item = self.get_current_item()
        if item and item.is_editable:
            self.editing = True
            self.edit_buffer = str(item.value)
            return True
        return False

    def cancel_editing(self):
        """Cancel current edit."""
        self.editing = False
        self.edit_buffer = ""
        self.message = None

    def apply_edit(self, new_value: Any) -> bool:
        """Apply edited value to current item."""
        item = self.get_current_item()
        if item:
            item.value = new_value
            self.editing = False
            self.edit_buffer = ""
            self.changes_made = True
            return True
        return False

    def set_message(self, message: str, is_error: bool = False):
        """Set status/error message."""
        self.message = message

    def clear_message(self):
        """Clear status/error message."""
        self.message = None


class MenuConfig(BaseModel):
    """Configuration for menu display."""

    title: str = Field(default="Settings", description="Menu title")
    show_hints: bool = Field(default=True, description="Show control hints")
    show_fixed: bool = Field(default=True, description="Show non-editable items")
    confirm_exit: bool = Field(default=True, description="Confirm before exit with changes")
    max_visible_items: int = Field(default=15, description="Max items visible at once")

    def get_hints(self) -> str:
        """Get control hints text."""
        if not self.show_hints:
            return ""

        hints = []
        hints.append("↑↓: Navigate")
        hints.append("Enter: Edit")
        hints.append("Esc: Cancel")
        hints.append("q: Save & Exit")

        return " | ".join(hints)