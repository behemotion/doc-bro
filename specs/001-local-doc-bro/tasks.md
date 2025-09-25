# Tasks: DocBro - Documentation Web Crawler

**Input**: Design documents from `/specs/001-local-doc-bro/`
**Prerequisites**: plan.md (required), research.md, data-model.md, contracts/

## Execution Flow (main)
```
1. Load plan.md from feature directory
   → Extract: Python 3.13.7, Qdrant 1.13.0 (Docker), Ollama (local), FastMCP 2.0, Scrapy 2.13.3
2. Load optional design documents:
   → data-model.md: 6 entities → model tasks
   → contracts/: 2 files → API test tasks
   → research.md: Hybrid deployment strategy → infrastructure tasks
3. Generate tasks by category:
   → Infrastructure: Docker Compose for Qdrant, local Ollama/Redis setup
   → Setup: project init, dependencies, configuration
   → Tests: CLI contract tests, MCP API tests, integration tests
   → Core: models, services, crawler, embeddings
   → CLI: 10 commands implementation
   → MCP: Server implementation
   → Polish: performance, docs
4. Apply task rules:
   → Different files = mark [P] for parallel
   → Tests before implementation (TDD)
5. Number tasks sequentially (T001-T045)
6. Return: SUCCESS (tasks ready for execution)
```

## Format: `[ID] [P?] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- Include exact file paths in descriptions

## Path Conventions
- **Single project**: `src/`, `tests/` at repository root
- **Docker**: `docker/` directory for containerized services
- Project structure per plan.md Option 1 with Docker addition

## Phase 3.1: Infrastructure Setup (T001-T006)
- [ ] T001 Create Docker Compose configuration for Qdrant 1.13.0 in docker/docker-compose.yml
- [ ] T002 Create project structure with src/{models,services,cli,lib}, tests/{contract,integration,unit}, and docker/
- [ ] T003 [P] Set up Ollama local installation script in scripts/setup-ollama.sh
- [ ] T004 [P] Set up Redis local installation script in scripts/setup-redis.sh (optional)
- [ ] T005 Initialize Python 3.13.7 project with pyproject.toml for UV packaging
- [ ] T006 Install core dependencies: qdrant-client, scrapy==2.13.3, fastmcp==2.0, click==8.3.0, rich==13.9.0

## Phase 3.2: Configuration & Environment (T007-T010)
- [ ] T007 [P] Configure pytest 8.x with async support and Docker test fixtures
- [ ] T008 [P] Set up configuration management in src/lib/config.py with Docker/local service detection
- [ ] T009 [P] Create Docker health checks and service connection utilities in src/lib/docker_utils.py
- [ ] T010 [P] Set up logging configuration with structured output in src/lib/logging.py

## Phase 3.3: Tests First (TDD) ⚠️ MUST COMPLETE BEFORE 3.4
**CRITICAL: These tests MUST be written and MUST FAIL before ANY implementation**

### CLI Command Tests
- [ ] T011 [P] Contract test for 'docbro crawl' command in tests/contract/test_cli_crawl.py
- [ ] T012 [P] Contract test for 'docbro list' command in tests/contract/test_cli_list.py
- [ ] T013 [P] Contract test for 'docbro query' command in tests/contract/test_cli_query.py
- [ ] T014 [P] Contract test for 'docbro rename' command in tests/contract/test_cli_rename.py
- [ ] T015 [P] Contract test for 'docbro delete' command in tests/contract/test_cli_delete.py
- [ ] T016 [P] Contract test for 'docbro recrawl' command in tests/contract/test_cli_recrawl.py
- [ ] T017 [P] Contract test for 'docbro export' command in tests/contract/test_cli_export.py
- [ ] T018 [P] Contract test for 'docbro import' command in tests/contract/test_cli_import.py
- [ ] T019 [P] Contract test for 'docbro config' command in tests/contract/test_cli_config.py
- [ ] T020 [P] Contract test for 'docbro status' command in tests/contract/test_cli_status.py

### MCP API Tests
- [ ] T021 [P] Contract test for MCP connection endpoint in tests/contract/test_mcp_connect.py
- [ ] T022 [P] Contract test for MCP search endpoint in tests/contract/test_mcp_search.py
- [ ] T023 [P] Contract test for MCP project list endpoint in tests/contract/test_mcp_projects.py

### Integration Tests
- [ ] T024 [P] Integration test for Docker Qdrant connection in tests/integration/test_docker_integration.py
- [ ] T025 [P] Integration test for crawling documentation in tests/integration/test_crawl_flow.py
- [ ] T026 [P] Integration test for search with RAG in tests/integration/test_search_rag.py
- [ ] T027 [P] Integration test for project lifecycle in tests/integration/test_project_lifecycle.py

## Phase 3.4: Core Implementation (ONLY after tests are failing)

### Data Models (T028-T033)
- [ ] T028 [P] Project model with SQLite persistence in src/models/project.py
- [ ] T029 [P] CrawledPage model in src/models/page.py
- [ ] T030 [P] Embedding model for vector storage in src/models/embedding.py
- [ ] T031 [P] CrawlSession tracking model in src/models/crawl_session.py
- [ ] T032 [P] QueryResult model in src/models/query_result.py
- [ ] T033 [P] AgentSession model for MCP connections in src/models/agent_session.py

### Core Services (T034-T039)
- [ ] T034 SQLite database setup and migrations in src/services/database.py
- [ ] T035 Qdrant Docker client wrapper with collection management in src/services/vector_store.py
- [ ] T036 Scrapy spider for documentation crawling in src/services/crawler.py
- [ ] T037 Ollama local integration for embeddings in src/services/embeddings.py
- [ ] T038 LangChain 0.3.76 RAG implementation in src/services/rag.py
- [ ] T039 Redis local queue manager for crawl scheduling in src/services/queue.py

### CLI Commands (T040-T049)
- [ ] T040 Main CLI entry point with Click in src/cli/main.py
- [ ] T041 Crawl command with Docker Qdrant integration in src/cli/commands/crawl.py
- [ ] T042 List command with Rich tables and status indicators in src/cli/commands/list.py
- [ ] T043 Query command with RAG search in src/cli/commands/query.py
- [ ] T044 Rename command in src/cli/commands/rename.py
- [ ] T045 Delete command with confirmation in src/cli/commands/delete.py
- [ ] T046 Recrawl command with queue management in src/cli/commands/recrawl.py
- [ ] T047 Export command with archive creation in src/cli/commands/export.py
- [ ] T048 Import command with validation in src/cli/commands/import.py
- [ ] T049 Config and status commands with service health checks in src/cli/commands/admin.py

## Phase 3.5: Integration (T050-T053)
- [ ] T050 FastMCP 2.0 server with FastAPI 0.115.11 in src/services/mcp_server.py
- [ ] T051 WebSocket support for real-time updates in src/services/websocket.py
- [ ] T052 Service orchestration for Docker and local services in src/services/orchestrator.py
- [ ] T053 Error handling and retry logic for service connections in src/lib/middleware.py

## Phase 3.6: Polish (T054-T057)
- [ ] T054 [P] Unit tests for Docker utilities in tests/unit/test_docker_utils.py
- [ ] T055 Performance optimization for 1GB+ projects with Docker volumes
- [ ] T056 [P] Documentation generation with deployment guides in docs/
- [ ] T057 Package configuration for UV/UVX distribution with Docker Compose

## Dependencies
- Infrastructure (T001-T006) must complete first
- Configuration (T007-T010) after infrastructure
- Tests (T011-T027) before implementation (T028-T049)
- Models (T028-T033) before services (T034-T039)
- Services before CLI commands (T040-T049)
- Core implementation before integration (T050-T053)
- Everything before polish (T054-T057)

## Parallel Execution Examples

### Infrastructure Setup Sprint (T001-T006)
```bash
# After T001-T002 (sequential dependencies):
Task: "Set up Ollama local installation script in scripts/setup-ollama.sh"
Task: "Set up Redis local installation script in scripts/setup-redis.sh (optional)"
# T005-T006 sequential (dependencies)
```

### Configuration Sprint (T007-T010)
```bash
# Launch all configuration tasks together:
Task: "Configure pytest 8.x with async support and Docker test fixtures"
Task: "Set up configuration management in src/lib/config.py with Docker/local service detection"
Task: "Create Docker health checks and service connection utilities in src/lib/docker_utils.py"
Task: "Set up logging configuration with structured output in src/lib/logging.py"
```

### Test Creation Sprint (T011-T023)
```bash
# Launch all CLI contract tests together:
Task: "Contract test for 'docbro crawl' command in tests/contract/test_cli_crawl.py"
Task: "Contract test for 'docbro list' command in tests/contract/test_cli_list.py"
Task: "Contract test for 'docbro query' command in tests/contract/test_cli_query.py"
Task: "Contract test for 'docbro rename' command in tests/contract/test_cli_rename.py"
Task: "Contract test for 'docbro delete' command in tests/contract/test_cli_delete.py"
# ... (continue with T016-T023)
```

### Model Creation Sprint (T028-T033)
```bash
# Launch all model tasks together:
Task: "Project model with SQLite persistence in src/models/project.py"
Task: "CrawledPage model in src/models/page.py"
Task: "Embedding model for vector storage in src/models/embedding.py"
Task: "CrawlSession tracking model in src/models/crawl_session.py"
Task: "QueryResult model in src/models/query_result.py"
Task: "AgentSession model for MCP connections in src/models/agent_session.py"
```

## Notes
- **Docker Integration**: Qdrant runs in container, Python app connects via Docker network
- **Local Services**: Ollama and Redis installed natively for better performance
- **Service Detection**: Configuration automatically detects Docker vs local service availability
- **Health Checks**: All services have connection validation and retry logic
- Each CLI command from spec (crawl, list, query, rename, delete, recrawl, export, import, config, status) has dedicated test and implementation
- MCP API endpoints from contracts/mcp-api.yaml covered
- All 6 entities from data-model.md have model tasks
- Hybrid deployment: Qdrant (Docker) + Ollama/Redis (local) per updated plan
- Tests use pytest 8.x with Docker test fixtures
- [P] tasks work on different files with no dependencies
- Commit after each task completion

## Service Connection Matrix
| Service | Deployment | Connection | Health Check |
|---------|------------|------------|--------------|
| Qdrant | Docker | localhost:6333 | REST API ping |
| Ollama | Local | localhost:11434 | Model list |
| Redis | Local | localhost:6379 | INFO command |
| SQLite | Local | File system | File exists |

## Validation Checklist
*GATE: Checked before execution*

- ✅ All 10 CLI commands have corresponding tests
- ✅ All 6 entities have model tasks
- ✅ Both contract files (cli-api.yaml, mcp-api.yaml) have tests
- ✅ Docker Compose setup for Qdrant included
- ✅ Local installation scripts for Ollama/Redis provided
- ✅ Service orchestration and health checks implemented
- ✅ All tests come before implementation (T011-T027 before T028-T049)
- ✅ Parallel tasks work on independent files
- ✅ Each task specifies exact file path
- ✅ No [P] task modifies same file as another [P] task