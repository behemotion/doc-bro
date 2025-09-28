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

### 1.8 Setup Flag Combinations
- [ ] `docbro setup --init --force` - force reinitialize
- [ ] `docbro setup --init --auto --force` - auto with force
- [ ] `docbro setup --init --non-interactive --vector-store sqlite_vec`
- [ ] `docbro setup --uninstall --backup --dry-run` - preview with backup
- [ ] `docbro setup --reset --preserve-data --force` - reset keeping data
- [ ] `docbro setup --uninstall --preserve-data --backup`
- [ ] Test invalid combinations: `--init --uninstall`
- [ ] Test invalid combinations: `--init --reset`
- [ ] Test invalid combinations: `--uninstall --reset`

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
- [ ] `docbro crawl --update --all --parallel 4` - parallel updates
- [ ] `docbro crawl --update --all --parallel 1` - sequential updates
- [ ] `docbro crawl --update --all --quiet` - suppress progress
- [ ] `docbro crawl --update --all --debug` - detailed output
- [ ] Test batch with mixed project types
- [ ] Test batch interruption and resume
- [ ] Test batch with some failures

### 3.5 Crawl Flag Combinations
- [ ] `docbro crawl test --url https://example.com --max-pages 10 --depth 2 --rate-limit 0.5`
- [ ] `docbro crawl test --update --debug --quiet` - conflicting flags
- [ ] `docbro crawl test --url https://example.com --parallel 8 --rate-limit 10` - aggressive crawling
- [ ] `docbro crawl test --max-pages 1 --depth 0` - single page only
- [ ] Test crawl without project name (should fail)
- [ ] Test crawl with both --url and --update (should handle properly)

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

### 4.1 Interactive Mode
- [ ] `docbro upload` - launch interactive menu
- [ ] Test project selection navigation
- [ ] Test source type selection (local, http, ftp, sftp, smb)
- [ ] Test file browser navigation
- [ ] Test multi-file selection
- [ ] Test upload cancellation

### 4.2 Local File Upload
- [ ] `docbro upload files --project test1 --source /path/to/file --type local`
- [ ] `docbro upload files --project test1 --source /path/to/dir --type local --recursive`
- [ ] `docbro upload files --project test1 --source /path/to/dir --type local --recursive --exclude "*.tmp"`
- [ ] `docbro upload files --project test1 --source /path/to/file --type local --dry-run`
- [ ] `docbro upload files --project test1 --source /path/to/file --type local --overwrite ask`
- [ ] `docbro upload files --project test1 --source /path/to/file --type local --overwrite skip`
- [ ] `docbro upload files --project test1 --source /path/to/file --type local --overwrite overwrite`
- [ ] `docbro upload files --project test1 --source /path/to/file --type local --progress`
- [ ] Test upload with multiple --exclude patterns
- [ ] Test upload with non-existent file
- [ ] Test upload with permission denied
- [ ] Test upload of large files (>100MB)
- [ ] Test upload of binary files
- [ ] Test upload with symlinks
- [ ] Test upload with spaces in filename
- [ ] Test upload with Unicode filenames

### 4.3 HTTP/HTTPS Upload
- [ ] `docbro upload files --project test1 --source https://example.com/doc.pdf --type https`
- [ ] `docbro upload files --project test1 --source http://example.com/data.json --type http`
- [ ] `docbro upload files --project test1 --source https://example.com/file --type https --username user`
- [ ] Test URL upload with authentication
- [ ] Test URL upload with large files
- [ ] Test URL upload with timeout
- [ ] Test URL upload with redirects
- [ ] Test URL upload with SSL errors

### 4.4 FTP Upload
- [ ] `docbro upload files --project test1 --source ftp://server/path --type ftp`
- [ ] `docbro upload files --project test1 --source ftp://server/path --type ftp --username user`
- [ ] `docbro upload files --project test1 --source ftp://server/path --type ftp --recursive`
- [ ] Test FTP with anonymous access
- [ ] Test FTP with authentication
- [ ] Test FTP with passive mode
- [ ] Test FTP connection failures

### 4.5 SFTP Upload
- [ ] `docbro upload files --project test1 --source sftp://server/path --type sftp`
- [ ] `docbro upload files --project test1 --source sftp://server/path --type sftp --username user`
- [ ] `docbro upload files --project test1 --source sftp://server/path --type sftp --recursive`
- [ ] Test SFTP with password authentication
- [ ] Test SFTP with SSH key authentication
- [ ] Test SFTP with non-standard port
- [ ] Test SFTP connection failures

### 4.6 SMB Upload
- [ ] `docbro upload files --project test1 --source smb://server/share/path --type smb`
- [ ] `docbro upload files --project test1 --source smb://server/share/path --type smb --username user`
- [ ] `docbro upload files --project test1 --source smb://server/share/path --type smb --recursive`
- [ ] Test SMB with domain authentication
- [ ] Test SMB with guest access
- [ ] Test SMB connection failures

### 4.7 Status Monitoring
- [ ] `docbro upload status`
- [ ] `docbro upload status --project test1`
- [ ] `docbro upload status --operation upload_test1_12345`
- [ ] `docbro upload status --active`
- [ ] Test status during active upload
- [ ] Test status with completed uploads
- [ ] Test status with failed uploads
- [ ] Test status with no uploads

### 4.8 Advanced Upload Options
- [ ] Combination: `--recursive --exclude "*.log" --exclude "*.tmp"`
- [ ] Combination: `--dry-run --progress`
- [ ] Combination: `--overwrite skip --recursive`
- [ ] Test upload with project that doesn't exist
- [ ] Test upload with invalid source type
- [ ] Test upload with conflicting flags
- [ ] Test upload with insufficient disk space
- [ ] Test upload interruption and resume

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

### 6.1 Basic Health Checks
- [ ] `docbro health` - full health check
- [ ] `docbro health --system` - system checks only
- [ ] `docbro health --services` - external service checks only
- [ ] `docbro health --config` - configuration validity checks
- [ ] `docbro health --projects` - project-specific health checks
- [ ] `docbro health --verbose` - detailed diagnostic information
- [ ] `docbro health --timeout 5` - quick health check
- [ ] `docbro health --timeout 60` - thorough health check

### 6.2 Health Flag Combinations
- [ ] `docbro health --system --services` - multiple checks
- [ ] `docbro health --config --projects --verbose` - detailed subset
- [ ] `docbro health --services --timeout 1` - quick service check
- [ ] `docbro health --format json` - JSON output
- [ ] Test health with all flags combined
- [ ] Test health with no vector store configured
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

## 14. MCP Server Testing Strategy

### 14.1 Fix Module Import Issues
- [ ] Identify missing `src.services.project` module references
- [ ] Update import paths to new organization structure
- [ ] Test imports after fixing
- [ ] Verify all MCP dependencies are available

### 14.2 MCP Server Setup
- [ ] Start read-only server: `docbro serve --host 0.0.0.0 --port 9383`
- [ ] Start admin server: `docbro serve --admin --host 127.0.0.1 --port 9384`
- [ ] Verify both servers can run simultaneously
- [ ] Check server logs for startup errors
- [ ] Test server shutdown and restart

### 14.3 Local Testing with curl
- [ ] Test health endpoint: `curl http://localhost:9383/health`
- [ ] Test project list: `curl http://localhost:9383/projects`
- [ ] Test specific project: `curl http://localhost:9383/projects/{name}`
- [ ] Test search endpoint: `curl -X POST http://localhost:9383/search -H "Content-Type: application/json" -d '{"query":"test"}'`
- [ ] Test admin endpoints on port 9384
- [ ] Verify localhost-only restriction on admin server

### 14.4 MCP Protocol Testing
- [ ] Test MCP tool discovery endpoint
- [ ] Test MCP resource listing
- [ ] Test MCP prompt generation
- [ ] Generate MCP client configs in mcp/ directory
- [ ] Test with MCP test client (if available)

### 14.5 Claude Code Integration
- [ ] Configure Claude Code with read-only server
- [ ] Configure Claude Code with admin server
- [ ] Test project listing via Claude Code
- [ ] Test search functionality via Claude Code
- [ ] Test admin commands via Claude Code
- [ ] Verify blocked operations (uninstall, reset, delete-all)

### 14.6 Playwright MCP Testing
- [ ] Use Playwright to navigate to server endpoints
- [ ] Screenshot API responses
- [ ] Test concurrent requests
- [ ] Test error handling with invalid requests
- [ ] Monitor console logs for errors

### 14.7 Security Testing
- [ ] Verify admin server refuses non-localhost connections
- [ ] Test path traversal protection
- [ ] Test command injection protection
- [ ] Test resource limits and timeouts
- [ ] Verify operation restrictions work

## Test Execution Log

### Session 1: 2025-09-28 20:45
### Session 2: 2025-09-28 21:15

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

#### Session 2 Results:
- **MCP Server Fixed**: ✅ Server starts successfully after fixing imports
  - Fixed imports: ProjectService → ProjectManager, SearchService → RAGSearchService
  - Fixed embedding import path (embeddings.py not embedding.py)
  - Fixed VectorStoreFactory method (create_vector_store not create)

- **MCP Server Testing**: ✅ Basic functionality working
  - Health endpoint: Working (returns status)
  - Project list endpoint: Working (returns empty list - needs investigation)
  - Server starts on port 9392 successfully

- **Unit Test Status**: ❌ 7 import errors preventing test execution
  - ModuleNotFoundError: src.models.batch_operation
  - ImportError: ShortKeyValidator from short_key_validator
  - ModuleNotFoundError: src.services.error_handler
  - ImportError: FormatValidator from format_validator
  - ModuleNotFoundError: src.cli.post_install
  - ImportError: SourceType from upload models
  - ImportError: VectorStoreSettings from settings

- **Command Testing**: ✅ Basic commands working
  - Project creation: Working
  - Project listing: Working (4 projects created)
  - Server startup: Working

#### Overall Status:
- Unit Tests: ❌ Fail (7 import errors, 328 tests collected)
- Integration Tests: ⏳ Not run
- Contract Tests: ⏳ Not run
- Performance Tests: ⏳ Not run
- MCP Servers: ✅ Working (basic functionality)

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