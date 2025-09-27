# DocBro Project Constitution

## Core Principles

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
- **Domain-specific organization**: Crawler functionality organized under `src/logic/crawler/` with functional grouping:
  - `core/` - Essential crawling logic (DocumentationCrawler, BatchCrawler)
  - `analytics/` - Reporting and error tracking (ErrorReporter, CrawlReport)
  - `utils/` - Supporting utilities (ProgressReporter, CrawlProgressDisplay)
  - `models/` - Crawler-specific data structures (CrawlSession, Page, etc.)

### Breaking Changes
- Breaking changes are acceptable and expected
- Document changes clearly but do not provide compatibility layers
- Update all dependent code in the same changeset