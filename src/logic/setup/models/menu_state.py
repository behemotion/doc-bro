"""Menu state tracking model."""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator


class MenuState(BaseModel):
    """Tracks interactive menu navigation and selections."""

    current_menu: str = Field(
        default="main",
        description="Active menu identifier"
    )
    selected_index: int = Field(
        default=0,
        description="Current cursor position in menu"
    )
    menu_stack: List[str] = Field(
        default_factory=lambda: ["main"],
        description="Navigation history stack"
    )
    pending_changes: Dict[str, Any] = Field(
        default_factory=dict,
        description="Unsaved modifications"
    )
    help_visible: bool = Field(
        default=False,
        description="Whether help is currently displayed"
    )

    @field_validator("selected_index")
    @classmethod
    def validate_index_bounds(cls, v: int) -> int:
        """Validate that selected index is non-negative."""
        if v < 0:
            raise ValueError(f"Selected index must be non-negative: {v}")
        return v

    @field_validator("menu_stack")
    @classmethod
    def validate_menu_stack_depth(cls, v: List[str]) -> List[str]:
        """Prevent menu stack overflow."""
        max_depth = 10
        if len(v) > max_depth:
            raise ValueError(f"Menu stack depth exceeds maximum of {max_depth}")

        # Ensure stack is not empty
        if not v:
            return ["main"]

        return v

    def push_menu(self, menu_id: str) -> None:
        """Navigate to a new menu, pushing it onto the stack."""
        if len(self.menu_stack) >= 10:
            raise RuntimeError("Menu navigation stack overflow")

        self.menu_stack.append(menu_id)
        self.current_menu = menu_id
        self.selected_index = 0  # Reset selection for new menu

    def go_back(self) -> Optional[str]:
        """Navigate back to previous menu."""
        if len(self.menu_stack) <= 1:
            return None  # Already at root menu

        self.menu_stack.pop()  # Remove current menu
        self.current_menu = self.menu_stack[-1]
        self.selected_index = 0
        return self.current_menu

    def go_to_root(self) -> None:
        """Navigate directly to root menu."""
        self.menu_stack = ["main"]
        self.current_menu = "main"
        self.selected_index = 0
        self.pending_changes.clear()

    def add_pending_change(self, key: str, value: Any) -> None:
        """Add a change to pending modifications."""
        self.pending_changes[key] = value

    def has_pending_changes(self) -> bool:
        """Check if there are unsaved changes."""
        return bool(self.pending_changes)

    def save_changes(self) -> Dict[str, Any]:
        """Return pending changes and clear them."""
        changes = self.pending_changes.copy()
        self.pending_changes.clear()
        return changes

    def discard_changes(self) -> None:
        """Discard all pending changes."""
        self.pending_changes.clear()

    def toggle_help(self) -> bool:
        """Toggle help visibility and return new state."""
        self.help_visible = not self.help_visible
        return self.help_visible

    def move_selection(self, direction: int, max_items: int) -> int:
        """Move selection up or down with wrapping."""
        if max_items <= 0:
            return 0

        new_index = (self.selected_index + direction) % max_items
        self.selected_index = max(0, new_index)
        return self.selected_index

    def get_navigation_path(self) -> str:
        """Get current navigation path as string."""
        return " > ".join(self.menu_stack)

    def is_at_root(self) -> bool:
        """Check if currently at root menu."""
        return len(self.menu_stack) == 1 and self.current_menu == "main"

    class Config:
        """Pydantic configuration."""

        arbitrary_types_allowed = True