
# Implementation Plan: DocBro - Documentation Web Crawler

**Branch**: `001-local-doc-bro` | **Date**: 2025-09-25 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-local-doc-bro/spec.md`

## Execution Flow (/plan command scope)
```
1. Load feature spec from Input path
   → If not found: ERROR "No feature spec at {path}"
2. Fill Technical Context (scan for NEEDS CLARIFICATION)
   → Detect Project Type from context (web=frontend+backend, mobile=app+api)
   → Set Structure Decision based on project type
3. Fill the Constitution Check section based on the content of the constitution document.
4. Evaluate Constitution Check section below
   → If violations exist: Document in Complexity Tracking
   → If no justification possible: ERROR "Simplify approach first"
   → Update Progress Tracking: Initial Constitution Check
5. Execute Phase 0 → research.md
   → If NEEDS CLARIFICATION remain: ERROR "Resolve unknowns"
6. Execute Phase 1 → contracts, data-model.md, quickstart.md, agent-specific template file (e.g., `CLAUDE.md` for Claude Code, `.github/copilot-instructions.md` for GitHub Copilot, `GEMINI.md` for Gemini CLI, `QWEN.md` for Qwen Code or `AGENTS.md` for opencode).
7. Re-evaluate Constitution Check section
   → If new violations: Refactor design, return to Phase 1
   → Update Progress Tracking: Post-Design Constitution Check
8. Plan Phase 2 → Describe task generation approach (DO NOT create tasks.md)
9. STOP - Ready for /tasks command
```

**IMPORTANT**: The /plan command STOPS at step 7. Phases 2-4 are executed by other commands:
- Phase 2: /tasks command creates tasks.md
- Phase 3-4: Implementation execution (manual or via tools)

## Summary
DocBro is a documentation web crawler with fully local capabilities that creates searchable vector databases from crawled documentation websites. It supports multiple projects, provides a CLI interface, enables external agent connections via MCP protocol, and uses local embeddings via Ollama for semantic search with advanced RAG strategies.

## Technical Context
**Language/Version**: Python 3.11+
**Primary Dependencies**: Qdrant (vector database), Ollama (embeddings), MCP protocol server, Click (CLI), BeautifulSoup4 (web crawling)
**Storage**: Qdrant vector database for embeddings, SQLite for metadata, local filesystem for project management
**Testing**: pytest with async support
**Target Platform**: Linux/macOS/Windows with Docker support
**Project Type**: single - CLI tool with server component
**Performance Goals**: Process >1GB documentation per project, crawl rate configurable, sub-second query response times
**Constraints**: Fully local operation, no cloud dependencies, respect robots.txt and rate limits
**Scale/Scope**: Support multiple concurrent projects, handle documentation sites with thousands of pages, provide real-time query responses

## Constitution Check
*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Since no project-specific constitution has been established yet, applying general best practices:
- ✅ **Modularity**: Design uses separate services for crawling, vector storage, embeddings, and CLI
- ✅ **Testability**: All components can be tested independently with mocks
- ✅ **Simplicity**: Start with core functionality, avoid premature optimization
- ✅ **Single Responsibility**: Each service handles one specific domain
- ✅ **Local-First**: All operations work offline, no cloud dependencies

## Project Structure

### Documentation (this feature)
```
specs/[###-feature]/
├── plan.md              # This file (/plan command output)
├── research.md          # Phase 0 output (/plan command)
├── data-model.md        # Phase 1 output (/plan command)
├── quickstart.md        # Phase 1 output (/plan command)
├── contracts/           # Phase 1 output (/plan command)
└── tasks.md             # Phase 2 output (/tasks command - NOT created by /plan)
```

### Source Code (repository root)
```
# Option 1: Single project (DEFAULT)
src/
├── models/
├── services/
├── cli/
└── lib/

tests/
├── contract/
├── integration/
└── unit/

# Option 2: Web application (when "frontend" + "backend" detected)
backend/
├── src/
│   ├── models/
│   ├── services/
│   └── api/
└── tests/

frontend/
├── src/
│   ├── components/
│   ├── pages/
│   └── services/
└── tests/

# Option 3: Mobile + API (when "iOS/Android" detected)
api/
└── [same as backend above]

ios/ or android/
└── [platform-specific structure]
```

**Structure Decision**: Option 1 (Single project) - This is a CLI tool with server component, not a web application

## Phase 0: Outline & Research
1. **Extract unknowns from Technical Context** above:
   - For each NEEDS CLARIFICATION → research task
   - For each dependency → best practices task
   - For each integration → patterns task

2. **Generate and dispatch research agents**:
   ```
   For each unknown in Technical Context:
     Task: "Research {unknown} for {feature context}"
   For each technology choice:
     Task: "Find best practices for {tech} in {domain}"
   ```

3. **Consolidate findings** in `research.md` using format:
   - Decision: [what was chosen]
   - Rationale: [why chosen]
   - Alternatives considered: [what else evaluated]

**Output**: research.md with all NEEDS CLARIFICATION resolved

## Phase 1: Design & Contracts
*Prerequisites: research.md complete*

1. **Extract entities from feature spec** → `data-model.md`:
   - Entity name, fields, relationships
   - Validation rules from requirements
   - State transitions if applicable

2. **Generate API contracts** from functional requirements:
   - For each user action → endpoint
   - Use standard REST/GraphQL patterns
   - Output OpenAPI/GraphQL schema to `/contracts/`

3. **Generate contract tests** from contracts:
   - One test file per endpoint
   - Assert request/response schemas
   - Tests must fail (no implementation yet)

4. **Extract test scenarios** from user stories:
   - Each story → integration test scenario
   - Quickstart test = story validation steps

5. **Update agent file incrementally** (O(1) operation):
   - Run `.specify/scripts/bash/update-agent-context.sh claude`
     **IMPORTANT**: Execute it exactly as specified above. Do not add or remove any arguments.
   - If exists: Add only NEW tech from current plan
   - Preserve manual additions between markers
   - Update recent changes (keep last 3)
   - Keep under 150 lines for token efficiency
   - Output to repository root

**Output**: data-model.md, /contracts/*, failing tests, quickstart.md, agent-specific file

## Phase 2: Task Planning Approach
*This section describes what the /tasks command will do - DO NOT execute during /plan*

**Task Generation Strategy**:
- Load `.specify/templates/tasks-template.md` as base
- Generate tasks from Phase 1 design docs (contracts, data model, quickstart)
- Each CLI command → contract test task [P]
- Each MCP method → API test task [P]
- Each entity → model creation task [P]
- Each service → service implementation task with tests
- Each user story → integration test task
- Implementation tasks to make tests pass

**Task Breakdown for DocBro**:
1. **Setup Tasks** (3-4 tasks):
   - Project structure creation
   - Docker compose configuration
   - Setup/installation scripts

2. **Model Tasks** (6 tasks):
   - Create Project, CrawlSession, Page, Chunk, QueryResult, AgentSession models

3. **Service Tasks** (12-14 tasks):
   - Database service (async SQLite operations)
   - Vector store service (Qdrant integration)
   - Embeddings service (Ollama integration)
   - Crawler service (httpx + BeautifulSoup4)
   - RAG service (search strategies)
   - MCP server (FastAPI + WebSocket)

4. **CLI Tasks** (10 tasks):
   - One task per CLI command (create, crawl, list, search, rename, remove, status, config, serve, help)

5. **Test Tasks** (8-10 tasks):
   - Contract tests for CLI commands
   - Contract tests for MCP API
   - Integration tests for crawling flow
   - Integration tests for search flow
   - End-to-end quickstart validation

**Ordering Strategy**:
- TDD order: Tests written before implementation
- Dependency order: Models → Services → CLI → Integration
- Mark [P] for parallel execution (independent files)
- Group related tasks for logical progression

**Estimated Output**: 40-45 numbered, ordered tasks in tasks.md

**IMPORTANT**: This phase is executed by the /tasks command, NOT by /plan

## Phase 3+: Future Implementation
*These phases are beyond the scope of the /plan command*

**Phase 3**: Task execution (/tasks command creates tasks.md)  
**Phase 4**: Implementation (execute tasks.md following constitutional principles)  
**Phase 5**: Validation (run tests, execute quickstart.md, performance validation)

## Complexity Tracking
*Fill ONLY if Constitution Check has violations that must be justified*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |


## Progress Tracking
*This checklist is updated during execution flow*

**Phase Status**:
- [x] Phase 0: Research complete (/plan command)
- [x] Phase 1: Design complete (/plan command)
- [x] Phase 2: Task planning complete (/plan command - describe approach only)
- [ ] Phase 3: Tasks generated (/tasks command)
- [ ] Phase 4: Implementation complete
- [ ] Phase 5: Validation passed

**Gate Status**:
- [x] Initial Constitution Check: PASS
- [x] Post-Design Constitution Check: PASS
- [x] All NEEDS CLARIFICATION resolved
- [x] Complexity deviations documented (none required)

---
*Based on Constitution v2.1.1 - See `/memory/constitution.md`*
