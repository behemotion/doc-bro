# DocBro Comprehensive Testing Plan

## Testing Objectives
- Validate all CLI commands with various flag combinations
- Test error handling and edge cases
- Verify data persistence and integrity
- Ensure proper service integration
- Validate security boundaries
- Test performance under load
- Verify MCP server functionality

## 1. Setup Command Testing

### 1.1 Interactive Mode
- [ ] Run `docbro setup` without flags - verify interactive menu appears
- [ ] Test arrow navigation (↑/↓) in menu
- [ ] Test number selection (1-9) in menu
- [ ] Test vim keys (j/k) navigation
- [ ] Test help display (?)
- [ ] Test escape/quit (q/ESC)
- [ ] Select each menu option and verify proper routing

### 1.2 Initialization Testing
- [ ] `docbro setup --init` - test interactive initialization
- [ ] `docbro setup --init --auto` - test automatic initialization
- [ ] `docbro setup --init --force` - test forced initialization
- [ ] `docbro setup --init --non-interactive` - test non-interactive mode
- [ ] `docbro setup --init --vector-store sqlite_vec` - test SQLite-vec selection
- [ ] `docbro setup --init --vector-store qdrant` - test Qdrant selection
- [ ] `docbro setup --init --vector-store invalid` - verify error handling
- [ ] Test initialization when already initialized (should warn)
- [ ] Test initialization with insufficient permissions
- [ ] Test initialization with disk space issues (mock)
- [ ] Test initialization with Python version < 3.13 (if possible)

### 1.3 Configuration Testing
- [ ] `docbro setup --config` - test configuration display
- [ ] `docbro setup --config --show` - test detailed config display
- [ ] `docbro setup --config --edit` - test config editing
- [ ] Test config file corruption recovery
- [ ] Test invalid YAML in config file
- [ ] Test missing config file handling

### 1.4 Uninstall Testing
- [ ] `docbro setup --uninstall` - test interactive uninstall
- [ ] `docbro setup --uninstall --force` - test forced uninstall
- [ ] `docbro setup --uninstall --preserve-data` - test data preservation
- [ ] `docbro setup --uninstall --dry-run` - test dry run mode
- [ ] Test uninstall with active projects
- [ ] Test uninstall with running servers
- [ ] Verify all directories are cleaned up properly
- [ ] Verify MCP configs are removed

### 1.5 Reset Testing
- [ ] `docbro setup --reset` - test full reset
- [ ] `docbro setup --reset --preserve-data` - test data preservation
- [ ] `docbro setup --reset --force` - test forced reset
- [ ] Test reset with corrupted state
- [ ] Test reset recovery mechanisms

### 1.6 Status Testing
- [ ] `docbro setup --status` - test status display
- [ ] Test status with all services running
- [ ] Test status with services partially available
- [ ] Test status with no services available

### 1.7 Edge Cases & Errors
- [ ] Test conflicting flags (e.g., --init --uninstall)
- [ ] Test multiple operations flags
- [ ] Test with read-only filesystem
- [ ] Test with network issues (for Qdrant/Ollama detection)
- [ ] Test Unicode in paths and configurations
- [ ] Test extremely long project names
- [ ] Test special characters in inputs

## 2. Project Command Testing

### 2.1 Project Creation
- [ ] `docbro project --create test1 --type crawling`
- [ ] `docbro project --create test2 --type data`
- [ ] `docbro project --create test3 --type storage`
- [ ] `docbro project --create "test 4" --type crawling --description "Test with spaces"`
- [ ] Test creation with duplicate names (should fail)
- [ ] Test creation with invalid type
- [ ] Test creation without required flags
- [ ] Test creation with very long description
- [ ] Test creation with special characters in name
- [ ] Test creation with reserved names (., .., /, etc.)
- [ ] Test creation when at project limit

### 2.2 Project Listing
- [ ] `docbro project --list` - basic listing
- [ ] `docbro project --list --verbose` - detailed listing
- [ ] `docbro project --list --status active`
- [ ] `docbro project --list --status inactive`
- [ ] `docbro project --list --limit 5`
- [ ] `docbro project --list --format json`
- [ ] `docbro project --list --format table`
- [ ] Test listing with no projects
- [ ] Test listing with 100+ projects
- [ ] Test listing with corrupted project data

### 2.3 Project Display
- [ ] `docbro project --show test1`
- [ ] `docbro project --show test1 --detailed`
- [ ] `docbro project --show test1 --format json`
- [ ] Test show with non-existent project
- [ ] Test show with special characters in name

### 2.4 Project Update
- [ ] `docbro project --update test1 --description "Updated description"`
- [ ] `docbro project --update test1 --settings '{"key": "value"}'`
- [ ] `docbro project --update test1 --status inactive`
- [ ] Test update with invalid JSON settings
- [ ] Test update with non-existent project
- [ ] Test concurrent updates (race conditions)

### 2.5 Project Removal
- [ ] `docbro project --remove test1`
- [ ] `docbro project --remove test1 --confirm`
- [ ] `docbro project --remove test1 --backup`
- [ ] `docbro project --remove test1 --force`
- [ ] Test removal of non-existent project
- [ ] Test removal of project with active crawl
- [ ] Test removal of project being served
- [ ] Verify data cleanup after removal

### 2.6 Interactive Mode
- [ ] `docbro project` without flags - test interactive menu
- [ ] Test all interactive menu options
- [ ] Test navigation in project selection

## 3. Crawl Command Testing

### 3.1 Basic Crawling
- [ ] `docbro crawl test-crawl --url https://example.com`
- [ ] `docbro crawl test-crawl --url https://example.com --max-pages 10`
- [ ] `docbro crawl test-crawl --url https://example.com --depth 2`
- [ ] `docbro crawl test-crawl --url https://example.com --rate-limit 0.5`
- [ ] Test crawl with existing project name (update mode)
- [ ] Test crawl with invalid URL
- [ ] Test crawl with unreachable URL
- [ ] Test crawl with redirect chains
- [ ] Test crawl with authentication required

### 3.2 Advanced Crawling
- [ ] Test crawl with custom headers
- [ ] Test crawl with cookies
- [ ] Test crawl with user agent
- [ ] Test crawl resume after interruption
- [ ] Test crawl with --exclude patterns
- [ ] Test crawl with --include patterns
- [ ] Test JavaScript-heavy sites
- [ ] Test sites with rate limiting
- [ ] Test sites with cloudflare protection

### 3.3 Batch Operations
- [ ] `docbro crawl --update test-crawl`
- [ ] `docbro crawl --update --all`
- [ ] Test batch with mixed project types
- [ ] Test batch interruption and resume
- [ ] Test batch with some failures

### 3.4 Error Handling
- [ ] Test crawl with 404 errors
- [ ] Test crawl with 500 errors
- [ ] Test crawl with timeout
- [ ] Test crawl with SSL errors
- [ ] Test crawl with infinite loops
- [ ] Test crawl with circular references
- [ ] Test crawl memory limits
- [ ] Test crawl disk space limits

## 4. Upload Command Testing

### 4.1 File Upload
- [ ] `docbro upload files --project test1 --source /path/to/file --type document`
- [ ] `docbro upload files --project test1 --source /path/to/dir --type code`
- [ ] Test upload with non-existent file
- [ ] Test upload with permission denied
- [ ] Test upload of large files (>100MB)
- [ ] Test upload of binary files
- [ ] Test upload with symlinks
- [ ] Test recursive directory upload

### 4.2 URL Upload
- [ ] `docbro upload files --project test1 --source https://example.com/doc.pdf --type pdf`
- [ ] Test URL upload with authentication
- [ ] Test URL upload with large files
- [ ] Test URL upload with timeout

### 4.3 Status Monitoring
- [ ] `docbro upload status`
- [ ] `docbro upload status --project test1`
- [ ] `docbro upload status --active`
- [ ] Test status during active upload
- [ ] Test status with completed uploads
- [ ] Test status with failed uploads

### 4.4 Interactive Upload
- [ ] `docbro upload` - test interactive mode
- [ ] Test file browser navigation
- [ ] Test multi-file selection
- [ ] Test upload cancellation

## 5. Serve Command Testing

### 5.1 Read-Only Server
- [ ] `docbro serve` - default settings
- [ ] `docbro serve --host 0.0.0.0 --port 9382`
- [ ] `docbro serve --host 127.0.0.1 --port 9383`
- [ ] `docbro serve --foreground`
- [ ] Test server with no projects
- [ ] Test server with multiple projects
- [ ] Test server port conflicts
- [ ] Test server shutdown gracefully

### 5.2 Admin Server
- [ ] `docbro serve --admin`
- [ ] `docbro serve --admin --host 127.0.0.1 --port 9384`
- [ ] Verify admin refuses non-localhost binding
- [ ] Test admin command execution
- [ ] Test admin security restrictions
- [ ] Verify blocked operations (uninstall, reset, delete-all)

### 5.3 API Endpoints Testing
- [ ] GET /health - health check
- [ ] GET /projects - list projects
- [ ] GET /projects/{name} - get project
- [ ] POST /search - semantic search
- [ ] GET /files/{project}/{path} - file access
- [ ] Test CORS headers
- [ ] Test authentication (if applicable)
- [ ] Test rate limiting
- [ ] Test concurrent requests
- [ ] Test malformed requests

### 5.4 MCP Protocol Testing
- [ ] Test MCP tool discovery
- [ ] Test MCP resource listing
- [ ] Test MCP prompt generation
- [ ] Test MCP error handling
- [ ] Test MCP with Claude Code
- [ ] Test MCP with other clients

## 6. Health Command Testing

- [ ] `docbro health` - full health check
- [ ] `docbro health --system` - system checks
- [ ] `docbro health --services` - service checks
- [ ] `docbro health --config` - configuration checks
- [ ] `docbro health --projects` - project checks
- [ ] `docbro health --format json`
- [ ] Test health with degraded services
- [ ] Test health with critical failures

## 7. Vector Store Testing

### 7.1 SQLite-vec Testing
- [ ] Initialize with SQLite-vec
- [ ] Create project with SQLite-vec
- [ ] Perform searches with SQLite-vec
- [ ] Test concurrent access to SQLite-vec
- [ ] Test SQLite-vec corruption recovery
- [ ] Test SQLite-vec migration
- [ ] Test SQLite-vec performance with 10k+ documents

### 7.2 Qdrant Testing
- [ ] Initialize with Qdrant
- [ ] Verify Qdrant connection
- [ ] Create project with Qdrant
- [ ] Perform searches with Qdrant
- [ ] Test Qdrant connection loss
- [ ] Test Qdrant restart recovery
- [ ] Test Qdrant data persistence

### 7.3 Provider Switching
- [ ] Switch from SQLite-vec to Qdrant
- [ ] Switch from Qdrant to SQLite-vec
- [ ] Test data migration between providers
- [ ] Test fallback mechanisms

## 8. Integration Testing

### 8.1 End-to-End Workflows
- [ ] Complete setup → project → crawl → search workflow
- [ ] Setup → upload → serve → query workflow
- [ ] Multi-project management workflow
- [ ] Backup and restore workflow

### 8.2 Service Integration
- [ ] Ollama embedding generation
- [ ] Docker container management
- [ ] Git integration (if applicable)
- [ ] File system operations

### 8.3 Performance Testing
- [ ] Crawl 1000+ pages
- [ ] Handle 10+ concurrent crawls
- [ ] Search across 100k+ documents
- [ ] Serve 100+ concurrent requests
- [ ] Memory usage under load
- [ ] CPU usage optimization

## 9. Security Testing

### 9.1 Input Validation
- [ ] SQL injection attempts
- [ ] Command injection attempts
- [ ] Path traversal attempts
- [ ] XSS in web interface
- [ ] CSRF protection
- [ ] File upload security

### 9.2 Access Control
- [ ] Admin server localhost restriction
- [ ] File access permissions
- [ ] Project isolation
- [ ] API authentication

### 9.3 Data Security
- [ ] Sensitive data handling
- [ ] Credential storage
- [ ] Log sanitization
- [ ] Secure defaults

## 10. Error Recovery Testing

### 10.1 Crash Recovery
- [ ] Kill process during crawl
- [ ] Kill process during upload
- [ ] Kill process during initialization
- [ ] Power failure simulation
- [ ] Disk full scenarios

### 10.2 Data Recovery
- [ ] Corrupted database recovery
- [ ] Partial write recovery
- [ ] Transaction rollback
- [ ] Backup restoration

### 10.3 Service Recovery
- [ ] Service restart handling
- [ ] Connection retry logic
- [ ] Graceful degradation
- [ ] Fallback mechanisms

## 11. Test Suite Execution

### 11.1 Unit Tests
- [ ] Run `pytest tests/unit/ -v`
- [ ] Fix any failing unit tests
- [ ] Achieve >80% coverage

### 11.2 Integration Tests
- [ ] Run `pytest tests/integration/ -v`
- [ ] Fix any failing integration tests
- [ ] Verify all flows work

### 11.3 Contract Tests
- [ ] Run `pytest tests/contract/ -v`
- [ ] Fix any API contract violations
- [ ] Verify backward compatibility

### 11.4 Performance Tests
- [ ] Run `pytest tests/performance/ -v`
- [ ] Verify <30s installation
- [ ] Verify response time SLAs

### 11.5 Package Verification
- [ ] Run `./.verify-package.sh`
- [ ] Fix any import issues
- [ ] Verify clean installation

## 12. Environment Testing

### 12.1 Operating Systems
- [ ] macOS (current environment)
- [ ] Linux (Docker/VM if needed)
- [ ] Windows WSL (if available)

### 12.2 Python Versions
- [ ] Python 3.13 (required minimum)
- [ ] Python 3.14 (if available)

### 12.3 Dependency Versions
- [ ] Latest UV version
- [ ] Minimum UV version (0.8)
- [ ] Latest dependency updates
- [ ] Dependency conflicts

## 13. Documentation Testing

### 13.1 CLI Help
- [ ] `docbro --help`
- [ ] `docbro setup --help`
- [ ] `docbro project --help`
- [ ] `docbro crawl --help`
- [ ] `docbro upload --help`
- [ ] `docbro serve --help`
- [ ] Verify all help text is accurate

### 13.2 Error Messages
- [ ] Verify error messages are helpful
- [ ] Verify error suggestions work
- [ ] Verify stack traces are meaningful

## 14. MCP Server Local Setup

### 14.1 Configuration
- [ ] Generate MCP configs in mcp/ directory
- [ ] Configure read-only server
- [ ] Configure admin server
- [ ] Test with Claude Code

### 14.2 Testing
- [ ] Connect Claude Code to servers
- [ ] Execute read operations
- [ ] Execute admin operations
- [ ] Verify security boundaries

## Test Execution Log

### Session Start: 2025-09-28 20:45

#### Issues Found:
1. **Project creation error** - 'dict' object has no attribute 'data' when accessing project attributes
2. **Project listing error** - 'str' object has no attribute 'value' when displaying project type/status
3. **Module not found** - src.lib was not being packaged due to .gitignore excluding lib/
4. **Crawl command issue** - Unable to find existing projects (database connection issue)
5. **MCP server error** - No module named 'src.services.project'
6. **Test import errors** - Multiple missing modules in unit tests (batch_operation, error_handler, etc.)
7. **Deprecated Pydantic validators** - Using V1 style @validator instead of V2 @field_validator

#### Fixes Applied:
1. ✅ Fixed project creation by properly converting settings dict to ProjectConfig object
2. ✅ Fixed project listing by safely handling both enum and string types for type/status
3. ✅ Fixed .gitignore to exclude only top-level /lib/, not src/lib/
4. ✅ Added lib and logic to package by fixing src/__init__.py (then removed to fix circular import)
5. ⏳ MCP server module issues need investigation
6. ⏳ Test module imports need fixing
7. ⏳ Pydantic validators need migration to V2 style

#### Final Status:
- Unit Tests: ❌ Fail (7 import errors, 43 tests collected)
- Integration Tests: ⏳ Not run
- Contract Tests: ⏳ Not run
- Performance Tests: ⏳ Not run
- MCP Servers: ❌ Issues (missing module errors)

### Notes:
- Project creation and listing now work correctly
- Package structure issues mostly resolved (lib now included)
- Still have module reference issues in tests and MCP server
- Need to update deprecated Pydantic validators
- Crawl command has project lookup issues

## Priority Order

1. **Critical**: Setup initialization, project creation, basic crawling
2. **High**: Server operations, MCP functionality, search operations
3. **Medium**: Upload functionality, batch operations, health checks
4. **Low**: Edge cases, performance optimization, documentation

## Success Criteria

- All critical and high priority tests pass
- No data loss scenarios
- Security boundaries enforced
- MCP servers functional
- <30s installation time
- All test suites pass