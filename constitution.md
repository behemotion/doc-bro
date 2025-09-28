# DocBro Project Constitution

## Core Principles

### Universal Interface Consistency
**All interface elements and interaction methods MUST be universal across the application.** This ensures predictable user experience and maintainable codebase:
- **Navigation Systems**: All CLI prompts, menus, and interactive elements must use the universal arrow navigation system (`src/cli/utils/navigation.py`)
- **Keyboard Shortcuts**: Consistent key bindings across all interfaces (↑/↓ arrows, j/k vim keys, numbers, Enter, Escape/q, ? for help)
- **Visual Styling**: Uniform highlighting, colors, and layout patterns throughout the application
- **Cross-Platform Behavior**: Identical functionality on all supported platforms with graceful fallbacks
- **Interaction Patterns**: Same navigation logic for similar operations (choice selection, menu navigation, configuration)

**Mandatory Navigation System Requirements:**
1. **ArrowNavigator**: Every menu MUST support arrow key (↑/↓) navigation for sequential browsing
2. **AddressNavigator**: Every menu MUST support direct number (1-9) selection for quick access
3. **Y/N Confirmation Rule**: Yes/No prompts MUST use only y/n keys - NEVER numbered options (no "1. Yes 2. No")
4. **Descriptive Labels**: Every selectable option MUST display a clear, short description
5. **Status Indicators**: Options MUST show current status when applicable (e.g., "[active]", "[disabled]", "[installed]")

Any new interactive CLI component MUST use the established universal navigation patterns. Duplicate navigation implementations are prohibited.

### Backward Compatibility Policy
**DocBro does not maintain backward compatibility.** This project prioritizes clean architecture and rapid evolution over legacy support. When making changes:
- Old import paths will be removed without deprecation warnings
- API changes are implemented immediately without transition periods
- Configuration formats may change between releases
- Database schemas may require migration without automated upgrade paths

This approach enables aggressive refactoring and prevents technical debt accumulation.

## Development Guidelines

### Code Organization
- Prefer clean, logical structure over maintaining old patterns
- Consolidate scattered functionality into coherent modules
- Remove obsolete code paths immediately after refactoring
- **Universal Utilities**: Cross-application utilities centralized in `src/cli/utils/` for reuse across all CLI components
- **Domain-specific organization**: Crawler functionality organized under `src/logic/crawler/` with functional grouping:
  - `core/` - Essential crawling logic (DocumentationCrawler, BatchCrawler)
  - `analytics/` - Reporting and error tracking (ErrorReporter, CrawlReport)
  - `utils/` - Supporting utilities (ProgressReporter, CrawlProgressDisplay)
  - `models/` - Crawler-specific data structures (CrawlSession, Page, etc.)

### Interface Implementation Requirements
- **MANDATORY**: All new interactive CLI features must use `ArrowNavigator` from `src/cli/utils/navigation.py`
- **PROHIBITED**: Creating custom navigation, prompt, or menu systems
- **REQUIRED**: Consistent visual styling using established patterns (blue highlighting, arrow indicators)
- **ENFORCED**: Cross-platform compatibility with automatic fallback detection
- **VALIDATED**: All interactive components must support multiple input methods (arrows, vim keys, numbers)

**Specific Implementation Rules:**
- **Arrow Navigation**: ALWAYS enabled for sequential menu traversal
- **Number Navigation**: ALWAYS enabled for direct selection (AddressNavigator pattern)
- **Y/N Confirmations**: NEVER use numbered options - only accept y/n/yes/no keys
- **Option Display**: ALWAYS show descriptive label for each option
- **Status Display**: ALWAYS show current status in brackets when applicable (e.g., "[running]", "[stopped]", "[v1.2.3]")

### Breaking Changes
- Breaking changes are acceptable and expected
- Document changes clearly but do not provide compatibility layers
- Update all dependent code in the same changeset