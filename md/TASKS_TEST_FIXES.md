# Tasks: Test Suite Remediation

**Current Status**: 848 passing, 980 failing, 181 skipped
**Goal**: Fix or delete all legacy tests, implement missing features for new tests
**Input**: Test suite analysis from test run on 2025-09-29

## Test Analysis Summary

### Category 1: Legacy Tests (DELETE - ~150 tests)
Tests using removed/refactored classes that no longer exist:
- ProjectManager → Now uses Shelf/Box architecture
- UploadManager → Now uses unified fill command
- BatchCrawler → Functionality reorganized
- Old CLI command structure

### Category 2: New Feature Tests (IMPLEMENT - ~500 tests)
Tests for Phase 3.3 context-aware commands and Shelf-Box system:
- Context-aware CLI commands with wizard integration
- Shelf and Box CRUD operations
- MCP shelf endpoints
- Fill command type-based routing
- Enhanced box command features

### Category 3: Integration Tests (FIX - ~200 tests)
Tests requiring database/service setup:
- Qdrant/SQLite-vec context tests
- Network upload tests
- Performance tests requiring running services

### Category 4: Contract Tests (UPDATE - ~130 tests)
Tests with outdated contracts or incorrect assumptions:
- System check CLI tests
- Settings service tests
- Uninstall service tests

## Phase 3.1: Cleanup Legacy Tests

### T001-T010: Delete Legacy Project/Upload Tests
- [ ] T001 [P] Delete tests/contract/test_cli_batch_crawl.py (uses BatchCrawler/ProjectManager)
- [ ] T002 [P] Delete tests/contract/test_cli_crawl_update.py (uses ProjectManager)
- [ ] T003 [P] Delete tests/contract/test_cli_create_wizard.py (old wizard structure)
- [ ] T004 [P] Delete tests/contract/test_setup_wizard_contract.py (old wizard)
- [ ] T005 [P] Delete tests/contract/test_project_create_cli.py (uses ProjectManager)
- [ ] T006 [P] Delete tests/contract/test_project_list_cli.py (uses ProjectManager)
- [ ] T007 [P] Delete tests/contract/test_project_remove_cli.py (uses ProjectManager)
- [ ] T008 [P] Delete tests/contract/test_upload_files_cli.py (uses UploadManager)
- [ ] T009 [P] Review and update/delete tests/unit/test_upload_sources.py (may be salvageable)
- [ ] T010 [P] Review tests/integration/test_network_upload.py (may need updates for fill command)

### T011-T015: Review and Update/Delete Ambiguous Legacy Tests
- [ ] T011 Review tests/contract/test_cli_commands_existing.py - check if setup commands are current
- [ ] T012 Review tests/contract/test_command_aliases.py - verify aliases still exist
- [ ] T013 Review tests/contract/test_config_validation.py - check if config structure current
- [ ] T014 Review tests/unit/test_file_validation.py - may be salvageable for box/fill validation
- [ ] T015 Review tests/unit/test_box_model.py - check against new box model in src/models/box.py

## Phase 3.2: Implement Shelf Command Features (TDD)

### T016-T025: Shelf CLI Command Implementation
**Prerequisites**: Tests already exist in tests/contract/shelf/test_cli_shelf_commands.py (17 failing)

- [ ] T016 Implement shelf create command with wizard support in src/cli/commands/shelf.py
- [ ] T017 Implement shelf list command with verbose/filter options in src/cli/commands/shelf.py
- [ ] T018 Implement shelf inspect/show command in src/cli/commands/shelf.py
- [ ] T019 Implement shelf current (get/set) command in src/cli/commands/shelf.py
- [ ] T020 Implement shelf rename command in src/cli/commands/shelf.py
- [ ] T021 Implement shelf delete command with force/confirmation in src/cli/commands/shelf.py
- [ ] T022 Add shelf validation (name constraints, duplicates) in src/cli/commands/shelf.py
- [ ] T023 Integrate context service for shelf status detection in src/cli/commands/shelf.py
- [ ] T024 Integrate wizard orchestrator for shelf setup in src/cli/commands/shelf.py
- [ ] T025 Add interactive shelf menu support in src/cli/commands/shelf.py

## Phase 3.3: Implement Box Command Features (TDD)

### T026-T035: Box CLI Command Implementation
**Prerequisites**: Tests already exist in tests/contract/test_box_create.py (13 failing)

- [ ] T026 Implement box create with type validation (drag/rag/bag) in src/cli/commands/box.py
- [ ] T027 Implement box create with shelf assignment in src/cli/commands/box.py
- [ ] T028 Implement box create with description support in src/cli/commands/box.py
- [ ] T029 Implement box create with wizard integration in src/cli/commands/box.py
- [ ] T030 Add box name validation (globally unique, special chars) in src/cli/commands/box.py
- [ ] T031 Implement box inspect command with type-aware prompts in src/cli/commands/box.py
- [ ] T032 Implement box list with filtering (type, shelf) in src/cli/commands/box.py
- [ ] T033 Implement box add/remove to shelf operations in src/cli/commands/box.py
- [ ] T034 Implement box rename command in src/cli/commands/box.py
- [ ] T035 Implement box delete command with force in src/cli/commands/box.py

## Phase 3.4: Implement Fill Command Features (TDD)

### T036-T045: Fill Command Type-Based Routing
**Prerequisites**: Tests already exist in tests/contract/test_fill_command.py (14 failing)

- [ ] T036 Implement fill command with box type detection in src/cli/commands/fill.py
- [ ] T037 Implement drag box routing (website crawler) in src/cli/commands/fill.py
- [ ] T038 Implement rag box routing (document uploader) in src/cli/commands/fill.py
- [ ] T039 Implement bag box routing (file storage) in src/cli/commands/fill.py
- [ ] T040 Add source validation based on box type in src/cli/commands/fill.py
- [ ] T041 Integrate context service for box existence checks in src/cli/commands/fill.py
- [ ] T042 Add wizard prompts for missing boxes in src/cli/commands/fill.py
- [ ] T043 Implement type-specific flag handling (--max-pages, --chunk-size, etc.) in src/cli/commands/fill.py
- [ ] T044 Add progress reporting for fill operations in src/cli/commands/fill.py
- [ ] T045 Add error handling with type-specific messages in src/cli/commands/fill.py

## Phase 3.5: Implement MCP Shelf Endpoints

### T046-T060: MCP Server Shelf Integration
**Prerequisites**: Tests already exist in tests/contract/shelf/test_mcp_shelf_endpoints.py (21 failing)

#### Read-Only Server Endpoints
- [ ] T046 [P] Implement GET /shelf/list endpoint in src/logic/mcp/core/read_only_server.py
- [ ] T047 [P] Implement GET /shelf/{name} endpoint in src/logic/mcp/core/read_only_server.py
- [ ] T048 [P] Implement GET /shelf/current endpoint in src/logic/mcp/core/read_only_server.py
- [ ] T049 [P] Add shelf filter to existing /projects/list endpoint in src/logic/mcp/core/read_only_server.py
- [ ] T050 [P] Add shelf awareness to /projects/search endpoint in src/logic/mcp/core/read_only_server.py

#### Admin Server Endpoints
- [ ] T051 [P] Implement POST /admin/shelf/create endpoint in src/logic/mcp/core/admin_server.py
- [ ] T052 [P] Implement POST /admin/shelf/add-box endpoint in src/logic/mcp/core/admin_server.py
- [ ] T053 [P] Implement POST /admin/shelf/remove-box endpoint in src/logic/mcp/core/admin_server.py
- [ ] T054 [P] Implement POST /admin/shelf/set-current endpoint in src/logic/mcp/core/admin_server.py
- [ ] T055 [P] Implement DELETE /admin/shelf/{name} endpoint (localhost only) in src/logic/mcp/core/admin_server.py

#### MCP Service Layer
- [ ] T056 Create ShelfMcpService for shelf operations in src/logic/mcp/services/shelf_service.py
- [ ] T057 Add shelf filtering to ReadOnlyMcpService in src/logic/mcp/services/read_only_service.py
- [ ] T058 Add shelf operations to AdminMcpService in src/logic/mcp/services/admin_service.py
- [ ] T059 Update MCP models for shelf requests/responses in src/logic/mcp/models/
- [ ] T060 Add error handling for shelf not found in src/logic/mcp/utils/

## Phase 3.6: Fix Integration Tests

### T061-T070: Database and Service Integration
- [ ] T061 Fix Qdrant context tests (may need Qdrant running) in tests/integration/test_qdrant_context.py
- [ ] T062 Fix SQLite-vec context tests in tests/integration/test_sqlite_vec_context.py
- [ ] T063 Update network upload tests for new fill command in tests/integration/test_network_upload.py
- [ ] T064 Review and fix UV compliance tests in tests/test_uv_compliance_integration.py
- [ ] T065 Fix MCP write rejection security tests in tests/security/test_mcp_write_rejection.py
- [ ] T066 Update system check CLI tests for current architecture in tests/contract/test_cli_system_check.py
- [ ] T067 Fix settings service contract tests in tests/contract/test_settings_service.py
- [ ] T068 Fix uninstall service contract tests in tests/contract/test_uninstall_service_contract.py
- [ ] T069 Review box model unit tests in tests/unit/test_box_model.py
- [ ] T070 Update file validation unit tests in tests/unit/test_file_validation.py

## Phase 3.7: Fix Performance Tests

### T071-T080: Performance Test Updates
- [ ] T071 Update installation performance tests for current setup flow in tests/performance/test_speed.py
- [ ] T072 Fix MCP response time tests in tests/performance/test_mcp_response_time.py
- [ ] T073 Update system validation tests in tests/performance/test_system_validation.py
- [ ] T074 Fix memory usage tests in tests/performance/test_memory_usage.py
- [ ] T075 Update menu performance tests in tests/performance/test_menu_performance.py
- [ ] T076 Fix setup performance tests in tests/performance/test_setup_performance.py
- [ ] T077 Update setup time tests in tests/performance/test_setup_time.py
- [ ] T078 Fix SQLite-vec performance tests in tests/performance/test_sqlite_vec_*.py
- [ ] T079 Update UI performance tests in tests/performance/test_ui_performance.py
- [ ] T080 Fix uninstall speed tests in tests/performance/test_uninstall_speed.py

## Phase 3.8: Polish and Documentation

### T081-T090: Test Suite Cleanup
- [ ] T081 [P] Register custom pytest marks in pytest.ini (contract, unit, performance, etc.)
- [ ] T082 [P] Fix datetime.utcnow() deprecation in src/services/database_migrator.py
- [ ] T083 [P] Fix FastAPI on_event deprecation in src/logic/mcp/core/read_only_server.py
- [ ] T084 [P] Fix Pydantic v1 @validator in src/logic/mcp/models/command_execution.py
- [ ] T085 [P] Fix Pydantic json_encoders deprecation warnings
- [ ] T086 [P] Fix Pydantic class-based config deprecation warnings
- [ ] T087 [P] Fix Pydantic min_items → min_length deprecation
- [ ] T088 Run full test suite and verify >90% pass rate
- [ ] T089 Update CLAUDE.md with new test structure and patterns
- [ ] T090 Commit all test fixes with comprehensive message

## Dependencies

### Critical Path
1. Phase 3.1 (T001-T015) - Cleanup before implementation
2. Phase 3.2 (T016-T025) - Shelf commands (block Phase 3.3)
3. Phase 3.3 (T026-T035) - Box commands (block Phase 3.4)
4. Phase 3.4 (T036-T045) - Fill command (block Phase 3.5)
5. Phase 3.5 (T046-T060) - MCP endpoints (can run with Phase 3.6)
6. Phase 3.6 (T061-T070) - Integration fixes (independent)
7. Phase 3.7 (T071-T080) - Performance fixes (after 3.2-3.6)
8. Phase 3.8 (T081-T090) - Polish (after all others)

### Parallel Opportunities
- Phase 3.1: All T001-T015 can run in parallel (different files)
- Phase 3.5: T046-T050 (read-only) parallel, T051-T055 (admin) parallel
- Phase 3.8: T081-T087 can run in parallel (different files)

## Validation Checklist

- [ ] All legacy tests identified and deleted
- [ ] All new feature tests have corresponding implementations
- [ ] All integration tests updated for new architecture
- [ ] All deprecation warnings fixed
- [ ] Test pass rate > 90% (2000+ passing tests)
- [ ] No syntax errors or collection failures
- [ ] Performance tests pass with external services

## Estimated Effort

- **Phase 3.1 (Cleanup)**: 2-3 hours (delete ~15 files)
- **Phase 3.2 (Shelf)**: 6-8 hours (10 tasks, complex CLI)
- **Phase 3.3 (Box)**: 6-8 hours (10 tasks, complex CLI)
- **Phase 3.4 (Fill)**: 5-7 hours (10 tasks, routing logic)
- **Phase 3.5 (MCP)**: 8-10 hours (15 tasks, endpoints + service layer)
- **Phase 3.6 (Integration)**: 4-6 hours (10 tasks, various fixes)
- **Phase 3.7 (Performance)**: 3-5 hours (10 tasks, timing tests)
- **Phase 3.8 (Polish)**: 2-3 hours (10 tasks, deprecations + docs)

**Total**: 36-50 hours across 90 tasks

## Notes

- TDD approach: Tests already exist, implementation needed
- Many tasks are independent and can be parallelized
- Focus on Phases 3.2-3.5 for maximum test pass rate improvement
- Performance tests (Phase 3.7) may require running services
- Integration tests (Phase 3.6) may need database migrations