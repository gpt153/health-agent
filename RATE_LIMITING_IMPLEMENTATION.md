# API Rate Limiting Implementation

## Overview

This document describes the implementation of API rate limiting for the Health Agent API using SlowAPI.

## What Was Implemented

### 1. Configuration (src/config.py)

Added configurable rate limit storage:

```python
RATE_LIMIT_STORAGE_URL: str = os.getenv("RATE_LIMIT_STORAGE_URL", "memory://")
```

- **Development**: Uses `memory://` (in-memory storage, default)
- **Production**: Set to `redis://localhost:6379` for distributed rate limiting

### 2. Middleware (src/api/middleware.py)

Updated the limiter initialization to use configurable storage:

```python
from src.config import RATE_LIMIT_STORAGE_URL

limiter = Limiter(key_func=get_remote_address, storage_uri=RATE_LIMIT_STORAGE_URL)
```

### 3. API Routes (src/api/routes.py)

Applied rate limits to all API endpoints based on their usage patterns:

#### Chat Endpoint (10/minute)
- `POST /api/v1/chat` - AI calls are expensive

#### User & Tracking Endpoints (20/minute)
- `POST /api/v1/users` - Create user
- `GET /api/v1/users/{user_id}` - Get user profile
- `DELETE /api/v1/users/{user_id}` - Delete user
- `GET /api/v1/users/{user_id}/profile` - Get profile
- `PATCH /api/v1/users/{user_id}/profile` - Update profile
- `GET /api/v1/users/{user_id}/preferences` - Get preferences
- `PATCH /api/v1/users/{user_id}/preferences` - Update preferences
- `DELETE /api/v1/users/{user_id}/conversation` - Clear conversation
- `POST /api/v1/users/{user_id}/food` - Log food
- `GET /api/v1/users/{user_id}/food` - Get food summary
- `POST /api/v1/users/{user_id}/reminders` - Create reminder
- `GET /api/v1/users/{user_id}/reminders` - Get reminders
- `GET /api/v1/users/{user_id}/reminders/{reminder_id}/status` - Get reminder status

#### Analytics Endpoints (30/minute)
- `GET /api/v1/users/{user_id}/xp` - Get XP
- `GET /api/v1/users/{user_id}/streaks` - Get streaks
- `GET /api/v1/users/{user_id}/achievements` - Get achievements

#### Health Check (60/minute)
- `GET /api/health` - Health check (for monitoring systems)

## Rate Limit Response

When rate limit is exceeded, the API returns:

**Status Code**: `429 Too Many Requests`

**Response Body**:
```json
{
  "error": "Rate limit exceeded: X per 1 minute"
}
```

## Testing

### Validation Script

Run the validation script to verify implementation:

```bash
python validate_rate_limiting.py
```

This checks:
- Configuration is properly set up
- Middleware imports and uses the config
- All endpoints have appropriate rate limits
- SlowAPI is in requirements.txt

### Manual Testing

1. **Start the server**:
   ```bash
   python -m uvicorn src.api.server:app --reload --port 8080
   ```

2. **Test with curl** (example for health endpoint, 60/min limit):
   ```bash
   # Send 65 requests quickly
   for i in {1..65}; do
     echo "Request $i:"
     curl -X GET http://localhost:8080/api/health \
       -H "Authorization: Bearer YOUR_API_KEY" \
       -w " (Status: %{http_code})\n"
   done
   ```

3. **Expected behavior**:
   - First 60 requests: `200 OK`
   - Requests 61-65: `429 Too Many Requests`

4. **Test with automated script**:
   ```bash
   export API_KEY=your_api_key_here
   python test_rate_limiting.py
   ```

### Test for Chat Endpoint (10/minute)

```bash
# Send 15 requests quickly
for i in {1..15}; do
  echo "Request $i:"
  curl -X POST http://localhost:8080/api/v1/chat \
    -H "Authorization: Bearer YOUR_API_KEY" \
    -H "Content-Type: application/json" \
    -d '{"user_id":"test_user","message":"test"}' \
    -w " (Status: %{http_code})\n"
done
```

Expected:
- First 10 requests: `200 OK`
- Requests 11-15: `429 Too Many Requests`

## Configuration for Different Environments

### Development (.env)

```env
RATE_LIMIT_STORAGE_URL=memory://
```

Uses in-memory storage (simple, no setup required).

### Production (.env)

```env
RATE_LIMIT_STORAGE_URL=redis://localhost:6379
```

Requirements:
1. Install Redis: `sudo apt-get install redis-server`
2. Start Redis: `sudo systemctl start redis`
3. Verify Redis: `redis-cli ping` (should return "PONG")

### Docker Compose (Production)

Add Redis service to `docker-compose.yml`:

```yaml
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  api:
    environment:
      - RATE_LIMIT_STORAGE_URL=redis://redis:6379

volumes:
  redis_data:
```

## Benefits of This Implementation

1. **Security**: Prevents API abuse and DoS attacks
2. **Cost Control**: Protects against cost overruns on AI API calls (OpenAI, Anthropic)
3. **Resource Protection**: Prevents resource exhaustion
4. **Flexibility**: Different limits for different endpoint types based on usage patterns
5. **Production Ready**: Supports distributed rate limiting via Redis
6. **Monitoring Friendly**: Higher limits for health check endpoints

## Monitoring

To monitor rate limiting in production:

1. **Check logs**: SlowAPI logs rate limit violations
2. **Redis commands** (if using Redis storage):
   ```bash
   # View all rate limit keys
   redis-cli KEYS "slowapi:*"

   # Check rate limit for specific IP
   redis-cli GET "slowapi:127.0.0.1:/api/v1/chat"
   ```

3. **Add metrics**: Consider adding Prometheus metrics for rate limit hits

## Future Enhancements

1. **Per-user rate limiting**: Track by user ID instead of IP
2. **Tiered limits**: Different limits for different API key tiers
3. **Custom error responses**: More detailed rate limit information
4. **Whitelist**: Skip rate limiting for trusted IPs
5. **Burst allowance**: Allow short bursts above the limit

## References

- [SlowAPI Documentation](https://slowapi.readthedocs.io/)
- [Issue #60](https://github.com/your-repo/health-agent/issues/60)
- [CODEBASE_REVIEW.md](/.bmad/CODEBASE_REVIEW.md) - Security Issue 1.5
