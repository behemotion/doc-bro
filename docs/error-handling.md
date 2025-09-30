# Error Handling Guide - Context-Aware Commands

**DocBro Context Failures and Recovery**

This guide covers error scenarios, recovery procedures, and troubleshooting for context-aware command features including entity detection, wizards, and MCP integration.

## Error Categories

### 1. Entity Not Found Errors
### 2. Context Detection Failures
### 3. Wizard Session Errors
### 4. Configuration State Errors
### 5. MCP Integration Errors
### 6. Performance and Timeout Errors

---

## 1. Entity Not Found Errors

### Shelf Not Found

**Error Message**:
```
Shelf 'my-docs' not found.
Create it? (y/n):
```

**Cause**: Attempting to access a shelf that doesn't exist in the database.

**Recovery Options**:

**Option A: Create the shelf immediately**
```bash
# Respond 'y' to creation prompt
Create it? (y/n): y

# Optionally launch wizard for configuration
Launch setup wizard? (y/n): y
```

**Option B: Create manually with specific settings**
```bash
docbro shelf create my-docs --description "My documentation" --set-current
```

**Option C: List existing shelves**
```bash
docbro shelf list --verbose
```

**Prevention**:
- Enable verbose mode to see available shelves: `docbro shelf list -v`
- Use tab completion (if enabled) for shelf names
- Set current shelf to avoid specifying name repeatedly

---

### Box Not Found

**Error Message**:
```
Box 'api-docs' not found.
Create it? (y/n):
```

**Cause**: Attempting to access a box that doesn't exist.

**Recovery Options**:

**Option A: Create with type prompt**
```bash
# Respond 'y' to creation prompt
Create it? (y/n): y

# Select box type when prompted
Box type: (1) drag (2) rag (3) bag
→ 1
```

**Option B: Create explicitly with type**
```bash
docbro box create api-docs --type drag --shelf my-shelf --init
```

**Option C: List existing boxes**
```bash
docbro box list --shelf my-shelf --verbose
```

**Prevention**:
- Use `docbro box list` to verify box names before accessing
- Specify `--shelf` flag to disambiguate boxes with same name
- Enable context cache to reduce repeated lookups

---

## 2. Context Detection Failures

### Database Connection Error

**Error Message**:
```
Error: Failed to connect to database
Context detection unavailable
```

**Cause**: Database file corrupted, locked, or inaccessible.

**Recovery Steps**:

1. **Check database file permissions**
   ```bash
   ls -la ~/.local/share/docbro/docbro.db
   chmod 644 ~/.local/share/docbro/docbro.db
   ```

2. **Verify database isn't locked**
   ```bash
   lsof ~/.local/share/docbro/docbro.db
   # If locked, stop the locking process
   ```

3. **Test database integrity**
   ```bash
   sqlite3 ~/.local/share/docbro/docbro.db "PRAGMA integrity_check;"
   ```

4. **Restore from backup (if available)**
   ```bash
   cp ~/.local/share/docbro/backups/docbro.db.backup ~/.local/share/docbro/docbro.db
   ```

5. **Reset database (last resort)**
   ```bash
   docbro setup --reset --preserve-data
   ```

**Prevention**:
- Ensure sufficient disk space (>2GB free)
- Don't manually edit database files
- Enable automatic backups via config

---

### Context Cache Corruption

**Error Message**:
```
Warning: Context cache corrupted, rebuilding...
```

**Cause**: Cache data inconsistent with database state.

**Recovery**: Automatic - Cache is cleared and rebuilt from database.

**Manual Recovery** (if automatic fails):
```bash
# Clear context cache
docbro debug clear-context-cache

# Verify cache rebuild
docbro shelf list -v
```

**Prevention**:
- Allow automatic cache cleanup (don't disable)
- Avoid concurrent modifications from multiple terminals
- Use proper shutdown procedures (don't force-kill processes)

---

### Slow Context Detection (>500ms)

**Error Message**:
```
Warning: Context detection took 1200ms (expected <500ms)
Performance degraded - check database size and load
```

**Cause**: Large database, disk I/O issues, or system resource constraints.

**Recovery Steps**:

1. **Check database size**
   ```bash
   du -h ~/.local/share/docbro/docbro.db
   # If >500MB, consider cleanup
   ```

2. **Optimize database**
   ```bash
   docbro debug optimize-database
   ```

3. **Check system resources**
   ```bash
   # CPU usage
   top -o cpu | head -20

   # Disk I/O
   iostat -x 1 5

   # Memory
   free -h
   ```

4. **Reduce cache TTL if memory-constrained**
   ```bash
   # Edit ~/.config/docbro/settings.yaml
   context_cache_ttl: 180  # Reduce from 300s to 180s
   ```

**Prevention**:
- Regular database maintenance via `docbro debug optimize-database`
- Archive old shelves/boxes not actively used
- Monitor system resources during heavy operations

---

## 3. Wizard Session Errors

### Wizard Timeout

**Error Message**:
```
Wizard session expired (30 minutes of inactivity)
Please restart the wizard to continue.
```

**Cause**: No user input for 30 minutes during wizard session.

**Recovery**:
```bash
# Restart wizard from beginning
docbro shelf create my-docs --init

# Or create without wizard
docbro shelf create my-docs --description "Quick setup"
```

**Prevention**:
- Complete wizards within 30-minute window
- Save partial data externally if pause needed
- Use manual commands if interruptions expected

---

### Invalid Wizard Input

**Error Message**:
```
Error: Invalid port number '99999'
Port must be between 1024 and 65535
Please try again:
```

**Cause**: User input doesn't match validation requirements.

**Recovery**: Automatic - Wizard prompts for retry with validation hints.

**Common Validation Errors**:

**Port Numbers**:
```
Valid range: 1024-65535
Example: 9383
```

**URLs**:
```
Must start with http:// or https://
Example: https://docs.example.com
```

**File Paths**:
```
Must be absolute or relative valid path
Example: /home/user/docs or ./local/files
```

**Entity Names**:
```
Alphanumeric, underscores, hyphens only
Length: 1-64 characters
Example: my-docs, api_references, docs2024
```

---

### Wizard Interruption (Ctrl+C)

**Error Message**:
```
Wizard cancelled by user
Cleaning up partial session...
```

**Cause**: User pressed Ctrl+C during wizard.

**Recovery**: Automatic cleanup of partial state.

**To Resume**:
```bash
# Start fresh wizard session
docbro shelf create my-docs --init

# Or skip wizard and configure manually
docbro shelf create my-docs
# Then edit config: ~/.config/docbro/shelves/my-docs.yaml
```

**Prevention**:
- Review wizard steps before starting (`--help` flag)
- Use dry-run mode if available
- Have configuration data ready before starting

---

### Maximum Wizard Sessions Exceeded

**Error Message**:
```
Error: Maximum active wizard sessions (10) reached
Please complete or cancel existing wizards
```

**Cause**: Too many concurrent wizard sessions open.

**Recovery**:

1. **List active sessions**
   ```bash
   docbro debug wizard-sessions
   ```

2. **Cancel specific session**
   ```bash
   docbro debug cancel-wizard <session-id>
   ```

3. **Clear all stale sessions**
   ```bash
   docbro setup --reset-wizards
   ```

**Prevention**:
- Complete or cancel wizards promptly
- Don't leave wizards idle
- Use single wizard at a time unless necessary

---

## 4. Configuration State Errors

### Unconfigured Entity

**Error Message**:
```
Warning: Shelf 'my-docs' exists but is not configured
Run setup wizard? (y/n):
```

**Cause**: Entity created without wizard or manual configuration.

**Recovery**:

**Option A: Run wizard**
```bash
Run setup wizard? (y/n): y
```

**Option B: Manual configuration**
```bash
# Edit shelf config
vi ~/.config/docbro/shelves/my-docs.yaml

# Set configuration_state:
configuration_state:
  is_configured: true
  has_content: false
  configuration_version: "1.0"
```

**Prevention**:
- Always use `--init` flag for guided setup
- Review entity status after creation: `docbro shelf my-docs`

---

### Configuration Migration Needed

**Error Message**:
```
Notice: Configuration schema updated
Migrate 'my-docs' to latest version? (y/n):
```

**Cause**: DocBro version upgrade changed configuration schema.

**Recovery**:

**Option A: Auto-migrate**
```bash
Migrate 'my-docs' to latest version? (y/n): y
```

**Option B: Manual migration**
```bash
docbro debug migrate-config my-docs
```

**Option C: Export and recreate**
```bash
# Export data
docbro shelf export my-docs > backup.json

# Recreate with new schema
docbro shelf delete my-docs --force
docbro shelf create my-docs --init
docbro shelf import my-docs < backup.json
```

**Prevention**:
- Enable automatic migrations in settings
- Backup before major version upgrades
- Review migration notes in release changelog

---

## 5. MCP Integration Errors

### MCP Endpoint Not Available

**Error Message**:
```
Error: Context endpoint unavailable
MCP server may not be running
```

**Cause**: MCP server not started or crashed.

**Recovery**:

1. **Check server status**
   ```bash
   docbro health --services
   ```

2. **Start MCP servers**
   ```bash
   docbro serve
   # Or with specific ports
   docbro serve --host 0.0.0.0 --port 9383
   ```

3. **Check port availability**
   ```bash
   lsof -i :9383
   lsof -i :9384
   ```

4. **Review server logs**
   ```bash
   tail -f ~/.cache/docbro/logs/mcp-server.log
   ```

**Prevention**:
- Enable auto-start via wizard: `docbro serve --init`
- Monitor server health: `docbro health --services`
- Configure alerts for server downtime

---

### Port Already in Use

**Error Message**:
```
Error: Port 9383 already in use
Another service is running on this port
```

**Cause**: Another process using MCP server port.

**Recovery**:

**Option A: Find and stop conflicting process**
```bash
lsof -i :9383
kill <PID>
docbro serve
```

**Option B: Use different port**
```bash
docbro serve --port 9385
```

**Option C: Reconfigure via wizard**
```bash
docbro serve --init
# Wizard will detect conflict and suggest alternatives
```

**Prevention**:
- Use non-standard ports if conflicts common
- Document port assignments for your environment
- Use wizard which auto-detects conflicts

---

### MCP Client Connection Refused

**Error Message** (in AI assistant):
```
Connection refused: localhost:9383
MCP server not responding
```

**Cause**: Server not running, firewall blocking, or wrong host/port.

**Recovery**:

1. **Verify server is running**
   ```bash
   docbro health --services
   curl http://localhost:9383/health
   ```

2. **Check firewall rules**
   ```bash
   # macOS
   sudo /usr/libexec/ApplicationFirewall/socketfilterfw --listapps

   # Linux
   sudo ufw status
   ```

3. **Restart server in foreground for debugging**
   ```bash
   docbro serve --foreground --verbose
   ```

4. **Verify client configuration**
   ```bash
   cat ~/.config/claude-code/mcp.json
   # Ensure host and port match server settings
   ```

**Prevention**:
- Use wizard-generated client configs
- Test connection after server start: `curl localhost:9383/health`
- Document server URLs for team environments

---

## 6. Performance and Timeout Errors

### Context Detection Timeout

**Error Message**:
```
Error: Context detection timed out (>5s)
Unable to determine entity status
```

**Cause**: Database query taking too long due to size or system load.

**Recovery**:

1. **Retry with explicit name**
   ```bash
   # Specify exact entity name to avoid scanning
   docbro shelf my-docs --force-cache-bypass
   ```

2. **Optimize database**
   ```bash
   docbro debug optimize-database
   ```

3. **Reduce query scope**
   ```bash
   # Use specific shelf context
   docbro box my-box --shelf my-shelf
   ```

**Prevention**:
- Regular database optimization
- Archive inactive shelves
- Monitor database size and performance

---

### Wizard Step Transition Slow (>200ms)

**Error Message**:
```
Warning: Wizard step transition took 450ms (expected <200ms)
System may be under heavy load
```

**Cause**: System resource constraints or network latency (for networked validation).

**Recovery**:

1. **Check system load**
   ```bash
   uptime
   top -o cpu
   ```

2. **Close resource-intensive applications**

3. **Continue wizard or cancel and retry later**

**Prevention**:
- Run wizards during low-load periods
- Ensure adequate system resources
- Disable unnecessary background processes during setup

---

### Memory Limit Exceeded

**Error Message**:
```
Error: Wizard memory usage (75MB) exceeded limit (50MB)
Session terminated to prevent system impact
```

**Cause**: Wizard session consuming excessive memory, possibly due to large collected data.

**Recovery**:

1. **Restart wizard with smaller inputs**
   ```bash
   docbro shelf create my-docs --init
   # Provide shorter descriptions
   # Use fewer tags
   ```

2. **Check system memory**
   ```bash
   free -h
   # Ensure >4GB available
   ```

3. **Close other applications to free memory**

**Prevention**:
- Keep wizard inputs concise
- Don't paste large blocks of text into description fields
- Monitor system memory before starting wizards

---

## Common Troubleshooting Commands

### Diagnostic Commands

```bash
# System health check
docbro health --system --services --config

# View active wizard sessions
docbro debug wizard-sessions

# Check context cache status
docbro debug context-cache-stats

# View recent errors
docbro debug errors --last 10

# Database integrity check
docbro debug verify-database

# Clear all caches
docbro debug clear-caches

# View logs
tail -f ~/.cache/docbro/logs/docbro.log
```

### Reset Commands

```bash
# Clear context cache only
docbro debug clear-context-cache

# Reset all wizard sessions
docbro setup --reset-wizards

# Reset configuration (keep data)
docbro setup --reset --preserve-data

# Full reset (WARNING: deletes all data)
docbro setup --reset --force
```

### Performance Commands

```bash
# Optimize database
docbro debug optimize-database

# Rebuild indexes
docbro debug rebuild-indexes

# Analyze performance
docbro debug performance-report

# Test context detection speed
time docbro shelf my-docs

# Test wizard performance
docbro debug benchmark-wizard
```

---

## Error Log Analysis

### Log Locations

- **Main log**: `~/.cache/docbro/logs/docbro.log`
- **MCP server log**: `~/.cache/docbro/logs/mcp-server.log`
- **Wizard log**: `~/.cache/docbro/logs/wizard.log`
- **Error log**: `~/.cache/docbro/logs/errors.log`

### Log Levels

```bash
# Set log level in config
# ~/.config/docbro/settings.yaml
log_level: DEBUG  # DEBUG, INFO, WARNING, ERROR

# Or via environment variable
export DOCBRO_LOG_LEVEL=DEBUG
docbro shelf my-docs
```

### Common Log Patterns

**Context Detection Errors**:
```
ERROR: ContextService: Database query failed for shelf 'my-docs'
ERROR: ContextCache: Cache lookup failed, key='shelf:my-docs'
```

**Wizard Errors**:
```
ERROR: WizardOrchestrator: Session timeout for wizard_id='abc-123'
ERROR: WizardValidator: Invalid input for step 3, expected port number
```

**MCP Errors**:
```
ERROR: McpServer: Failed to bind to port 9383, address in use
ERROR: McpEndpoint: Context lookup failed for shelf 'nonexistent'
```

---

## Support and Reporting

### Before Reporting Issues

1. Check this error handling guide
2. Review logs for detailed error messages
3. Verify system health: `docbro health --system`
4. Try diagnostic commands above
5. Search existing issues: https://github.com/behemotion/doc-bro/issues

### Reporting New Issues

Include the following information:

```bash
# System information
docbro --version
uname -a
python --version

# Health check
docbro health --system --services --config

# Recent logs
tail -100 ~/.cache/docbro/logs/docbro.log

# Reproduction steps
1. Run command: docbro shelf create test --init
2. Expected: Wizard starts
3. Actual: Error message displayed
4. Error text: [paste error message]
```

### Getting Help

- **GitHub Issues**: https://github.com/behemotion/doc-bro/issues
- **Documentation**: https://github.com/behemotion/doc-bro/docs
- **Logs**: `~/.cache/docbro/logs/`
- **Debug mode**: `export DOCBRO_LOG_LEVEL=DEBUG`

---

## Quick Reference

| Error Type | Quick Fix | Documentation |
|------------|-----------|---------------|
| Entity not found | `docbro <entity> list` | Section 1 |
| Context detection | `docbro debug clear-context-cache` | Section 2 |
| Wizard timeout | Restart wizard | Section 3 |
| Config issues | `docbro setup --reset-wizards` | Section 4 |
| MCP errors | `docbro serve --init` | Section 5 |
| Performance | `docbro debug optimize-database` | Section 6 |