# Troubleshooting Guide

Common issues and solutions for the Health Agent system.

---

## Quick Diagnosis

| Symptom | Likely Cause | Section |
|---------|--------------|---------|
| Bot not responding | Token issue, bot offline | [Bot Issues](#bot-issues) |
| Database connection error | PostgreSQL not running | [Database Issues](#database-issues) |
| API 401 Unauthorized | Invalid API key | [API Issues](#api-issues) |
| Vision AI timeout | OpenAI/Anthropic API issue | [External API Issues](#external-api-issues) |
| Slow responses | Database query performance | [Performance Issues](#performance-issues) |

---

## Bot Issues

### Bot Not Responding to Messages

**Symptoms**: User sends message, no response

**Diagnosis**:
```bash
# Check bot logs
docker logs health-agent-bot --tail 50

# Check bot process
docker ps | grep health-agent-bot
```

**Solutions**:

1. **Invalid Telegram Token**
   ```bash
   # Verify token
   echo $TELEGRAM_BOT_TOKEN

   # Test token
   curl "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getMe"
   ```

2. **Bot Offline**
   ```bash
   # Restart bot
   docker compose restart health-agent-bot
   ```

3. **Telegram ID Not Whitelisted**
   ```bash
   # Check whitelist
   echo $ALLOWED_TELEGRAM_IDS

   # Add your ID
   export ALLOWED_TELEGRAM_IDS="123456789,987654321"
   docker compose up -d health-agent-bot
   ```

---

### Conflict: Terminated by Other getUpdates Request

**Error Message**: `"Conflict: terminated by other getUpdates request"`

**Cause**: Multiple bot instances running with same token

**Solution**:
```bash
# Stop all instances
docker compose down

# Kill any other processes using the token
pkill -f "python main.py"

# Start single instance
docker compose up -d health-agent-bot
```

---

### Bot Crashes on Startup

**Check Logs**:
```bash
docker logs health-agent-bot
```

**Common Causes**:

1. **Missing Environment Variables**
   ```bash
   # Check .env file exists
   cat .env

   # Verify required variables
   echo $DATABASE_URL
   echo $TELEGRAM_BOT_TOKEN
   ```

2. **Database Connection Failure**
   ```bash
   # Ensure postgres is running
   docker compose up -d postgres

   # Wait 10 seconds for postgres to initialize
   sleep 10

   # Then start bot
   docker compose up -d health-agent-bot
   ```

---

## Database Issues

### Connection Refused

**Error**: `psycopg.OperationalError: connection refused`

**Diagnosis**:
```bash
# Check postgres running
docker ps | grep postgres

# Check postgres logs
docker logs health-agent-db

# Test connection
psql -h localhost -p 5436 -U postgres -d health_agent
```

**Solutions**:

1. **PostgreSQL Not Running**
   ```bash
   docker compose up -d postgres
   ```

2. **Wrong Port**
   ```bash
   # Check docker-compose.yml
   grep "5436:5432" docker-compose.yml

   # Update DATABASE_URL
   export DATABASE_URL="postgresql://postgres:password@localhost:5436/health_agent"
   ```

3. **Firewall Blocking Port**
   ```bash
   # Check if port is listening
   netstat -an | grep 5436

   # Allow port in firewall (Linux)
   sudo ufw allow 5436
   ```

---

### Schema Mismatch

**Error**: `relation "food_entries" does not exist`

**Cause**: Migrations not run

**Solution**:
```bash
# Run migrations manually
for f in migrations/*.sql; do
    docker exec -i health-agent-db psql -U postgres health_agent < "$f"
done

# Or restart postgres (migrations auto-run)
docker compose restart postgres
```

---

### Duplicate Key Violation

**Error**: `duplicate key value violates unique constraint`

**Cause**: Trying to insert duplicate data

**Solutions**:

1. **Check Existing Data**
   ```sql
   SELECT * FROM users WHERE telegram_id = '123456789';
   ```

2. **Use ON CONFLICT** (in migrations)
   ```sql
   INSERT INTO users (telegram_id) VALUES ('123456789')
   ON CONFLICT (telegram_id) DO NOTHING;
   ```

---

## API Issues

### 401 Unauthorized

**Error**: `{"detail": "Invalid API key"}`

**Solution**:
```bash
# Check API key in request
curl -H "X-API-Key: your_key" http://localhost:8080/health

# Verify API keys in environment
echo $API_KEYS

# Add API key
export API_KEYS="test_key_123,prod_key_456"
docker compose up -d health-agent-api
```

---

### 429 Too Many Requests

**Error**: `{"detail": "Rate limit exceeded"}`

**Cause**: Too many requests from same IP

**Solution**:
- Wait 60 seconds
- Implement exponential backoff in client
- Increase rate limit (edit `src/api/app.py`)

---

### Port Already in Use

**Error**: `Address already in use: 8080`

**Solution**:
```bash
# Find process using port
lsof -i :8080

# Kill process
kill -9 <PID>

# Or change port
export API_PORT=8081
uvicorn src.api.app:app --port 8081
```

---

## External API Issues

### OpenAI API Rate Limit

**Error**: `RateLimitError: You exceeded your current quota`

**Solutions**:

1. **Check API Usage**
   - Visit https://platform.openai.com/usage

2. **Add Retries**
   - Already implemented in PydanticAI (retries=2)

3. **Fallback to Claude**
   ```python
   # Automatic fallback in multi-agent consensus
   # If OpenAI fails, Claude takes over
   ```

---

### USDA API Timeout

**Error**: `TimeoutError: USDA API request timed out`

**Solutions**:

1. **Increase Timeout**
   ```python
   # src/nutrition/usda_client.py
   client = httpx.AsyncClient(timeout=30.0)  # Increase from 10.0
   ```

2. **Cache Results**
   - USDA data rarely changes, cache for 24 hours

---

## Performance Issues

### Slow Message Responses

**Diagnosis**:
```python
# Check logs for timing info
# Look for slow operations (>2 seconds)
```

**Common Causes**:

1. **Vision AI Bottleneck**
   - Multi-agent consensus takes ~5 seconds
   - This is expected behavior

2. **Database Query Performance**
   ```sql
   -- Check slow queries
   SELECT query, mean_exec_time
   FROM pg_stat_statements
   ORDER BY mean_exec_time DESC
   LIMIT 10;
   ```

3. **Missing Database Indexes**
   ```sql
   -- Add index
   CREATE INDEX idx_food_entries_user_timestamp
   ON food_entries(user_id, timestamp DESC);
   ```

---

### High Memory Usage

**Check Memory**:
```bash
docker stats

# Expected:
# health-agent-bot: ~150MB
# postgres: ~200MB
```

**Solutions**:

1. **Reduce Database Connection Pool**
   ```python
   # src/db/connection.py
   pool = AsyncConnectionPool(min_size=2, max_size=5)  # Reduce from 10
   ```

2. **Clear Old Conversation History**
   ```sql
   -- Keep only last 1000 messages per user
   DELETE FROM conversation_history
   WHERE id NOT IN (
       SELECT id FROM conversation_history
       ORDER BY timestamp DESC
       LIMIT 1000
   );
   ```

---

## Logging and Debugging

### Enable Debug Logging

```bash
# Set environment variable
export LOG_LEVEL=DEBUG
docker compose up -d health-agent-bot

# View logs
docker logs -f health-agent-bot
```

### Log Locations

- **Docker**: `docker logs health-agent-bot`
- **Native**: `./production/logs/health_agent.log`
- **Database**: PostgreSQL logs in Docker container

### Structured Log Analysis

```bash
# Find errors
docker logs health-agent-bot 2>&1 | grep ERROR

# Find specific user's activity
docker logs health-agent-bot 2>&1 | grep "user_id=123456"

# Find tool calls
docker logs health-agent-bot 2>&1 | grep "Tool call"
```

---

## Data Recovery

### Corrupted User Data

**Symptoms**: Bot crashes when user sends message

**Solution**:
```bash
# Backup current data
cp production/data/123456/profile.md production/data/123456/profile.md.backup

# Reset user's profile
cat > production/data/123456/profile.md << 'EOF'
# User Profile

## Demographics
- Age:
- Height (cm):
- Weight (kg):

## Goals
-
EOF

# Restart bot
docker compose restart health-agent-bot
```

---

### Lost Database Data

**Restore from Backup**:
```bash
# Stop bot
docker compose stop health-agent-bot

# Restore database
docker exec -i health-agent-db psql -U postgres health_agent < /backups/health_agent_20250118.sql

# Start bot
docker compose start health-agent-bot
```

---

## Common Error Messages

### `ModuleNotFoundError: No module named 'src'`

**Cause**: Python path not set

**Solution**:
```bash
# Ensure running from project root
cd /path/to/health-agent

# Or set PYTHONPATH
export PYTHONPATH=$(pwd)
python main.py
```

---

### `AttributeError: 'NoneType' object has no attribute 'run_sync'`

**Cause**: Agent not initialized

**Solution**:
```python
# Check agent initialization in src/agent/__init__.py
# Ensure AGENT_MODEL environment variable is set
echo $AGENT_MODEL
```

---

### `FileNotFoundError: production/data/123456/profile.md`

**Cause**: User's data directory not created

**Solution**:
```bash
# Create user directory
mkdir -p production/data/123456

# Initialize profile.md
touch production/data/123456/profile.md
touch production/data/123456/preferences.md
```

---

## Getting Help

### Check Existing Issues

1. [GitHub Issues](https://github.com/gpt153/health-agent/issues)
2. Search for your error message
3. Check closed issues for solutions

### Create Issue

Include:
- Error message and stack trace
- Steps to reproduce
- Environment (Docker/native, OS, Python version)
- Relevant log excerpts

### Emergency Contacts

- **SCAR**: Mention @scar in GitHub issue
- **Developer**: Create issue with "bug" label

---

## Prevention

### Health Monitoring

```bash
# Create health check script
cat > /usr/local/bin/health_check.sh << 'EOF'
#!/bin/bash
# Check bot is running
docker ps | grep health-agent-bot || echo "Bot DOWN!"

# Check database
psql -h localhost -p 5436 -U postgres -d health_agent -c "SELECT 1;" || echo "DB DOWN!"

# Check API (if running)
curl -f http://localhost:8080/health || echo "API DOWN!"
EOF

chmod +x /usr/local/bin/health_check.sh

# Add to cron (every 5 minutes)
*/5 * * * * /usr/local/bin/health_check.sh >> /var/log/health_check.log 2>&1
```

---

## Related Documentation

- **Deployment**: [/docs/deployment/](../deployment/) - Deployment guides
- **Development**: [/docs/development/](../development/) - Development setup
- **Architecture**: [/docs/architecture/](../architecture/) - System architecture

## Revision History

- 2025-01-18: Initial troubleshooting guide created for Phase 3.7
