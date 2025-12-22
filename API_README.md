# Health Agent REST API

REST API for the AI Health Coach, enabling programmatic access to all agent functionality.

## Overview

This API provides direct access to the health agent without requiring Telegram. It supports:
- ✅ Chat with agent
- ✅ User management (profile, preferences)
- ✅ Memory operations (conversation history)
- ✅ Food logging and summaries
- ✅ Reminder management
- ✅ Gamification (XP, streaks, achievements)
- ✅ Health check endpoint

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Add to `.env`:

```bash
# REST API Configuration
RUN_MODE=api  # or 'both' for bot + API
API_HOST=0.0.0.0
API_PORT=8080
API_KEYS=test_key_123,scar_key_456,po_key_789
CORS_ORIGINS=http://localhost:3000
```

### 3. Run API Server

```bash
# Run API only
RUN_MODE=api python src/main.py

# Or run both Telegram bot and API
RUN_MODE=both python src/main.py
```

### 4. Test the API

```bash
# Health check
curl http://localhost:8080/api/health

# Chat endpoint
curl -X POST http://localhost:8080/api/v1/chat \
  -H "Authorization: Bearer test_key_123" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user",
    "message": "Hello, how are you?"
  }'
```

## Authentication

All endpoints (except `/api/health`) require API key authentication:

```
Authorization: Bearer YOUR_API_KEY
```

API keys are configured via the `API_KEYS` environment variable (comma-separated).

## Endpoints

### Health Check

```http
GET /api/health
```

No authentication required.

**Response:**
```json
{
  "status": "healthy",
  "database": "connected",
  "timestamp": "2025-12-22T12:00:00"
}
```

---

### Chat

```http
POST /api/v1/chat
```

Send a message to the agent and get a response.

**Request:**
```json
{
  "user_id": "user_123",
  "message": "What did I eat yesterday?",
  "message_history": [  // optional
    {"role": "user", "content": "I had pizza for lunch"},
    {"role": "assistant", "content": "Logged!"}
  ]
}
```

**Response:**
```json
{
  "response": "According to my records, you had...",
  "timestamp": "2025-12-22T12:00:00",
  "user_id": "user_123"
}
```

---

### User Management

#### Create User

```http
POST /api/v1/users
```

**Request:**
```json
{
  "user_id": "user_123",
  "profile": {
    "age": 30,
    "height_cm": 180,
    "weight_kg": 75
  }
}
```

#### Get User

```http
GET /api/v1/users/{user_id}
```

**Response:**
```json
{
  "user_id": "user_123",
  "profile": {
    "age": "30",
    "height_cm": "180",
    "weight_kg": "75"
  },
  "preferences": {
    "tone": "friendly",
    "brevity": "medium"
  }
}
```

#### Delete User

```http
DELETE /api/v1/users/{user_id}
```

---

### Profile & Preferences

#### Get Profile

```http
GET /api/v1/users/{user_id}/profile
```

#### Update Profile

```http
PATCH /api/v1/users/{user_id}/profile
```

**Request:**
```json
{
  "field": "weight_kg",
  "value": "76"
}
```

#### Get Preferences

```http
GET /api/v1/users/{user_id}/preferences
```

#### Update Preferences

```http
PATCH /api/v1/users/{user_id}/preferences
```

**Request:**
```json
{
  "preference": "tone",
  "value": "casual"
}
```

---

### Conversation

#### Clear Conversation History

```http
DELETE /api/v1/users/{user_id}/conversation
```

**Important:** This clears conversation history but preserves user profile, preferences, and long-term memory (patterns).

---

### Food Logging

#### Log Food

```http
POST /api/v1/users/{user_id}/food
```

**Request:**
```json
{
  "description": "Chicken breast with rice",
  "timestamp": "2025-12-22T12:00:00"  // optional
}
```

#### Get Food Summary

```http
GET /api/v1/users/{user_id}/food?date=2025-12-22
```

**Response:**
```json
{
  "date": "2025-12-22",
  "entries": [...],
  "total_calories": 1850.5,
  "total_protein": 120.3,
  "total_carbs": 180.2,
  "total_fat": 65.1
}
```

---

### Reminders

#### Create Reminder

```http
POST /api/v1/users/{user_id}/reminders
```

**Daily Reminder:**
```json
{
  "type": "daily",
  "message": "Take vitamin D",
  "daily_time": "09:00",
  "timezone": "Europe/Stockholm"
}
```

**One-Time Reminder:**
```json
{
  "type": "one_time",
  "message": "Check blood pressure",
  "trigger_time": "2025-12-22T15:00:00+01:00",
  "timezone": "Europe/Stockholm"
}
```

#### List Reminders

```http
GET /api/v1/users/{user_id}/reminders
```

#### Get Reminder Status

```http
GET /api/v1/users/{user_id}/reminders/{reminder_id}/status
```

**Response:**
```json
{
  "id": "rem_123",
  "triggered": true,
  "completed": true,
  "completed_at": "2025-12-22T09:05:00"
}
```

---

### Gamification

#### Get XP Status

```http
GET /api/v1/users/{user_id}/xp
```

**Response:**
```json
{
  "user_id": "user_123",
  "xp": 450,
  "level": 5,
  "tier": "Silver",
  "xp_to_next_level": 50
}
```

#### Get Streaks

```http
GET /api/v1/users/{user_id}/streaks
```

**Response:**
```json
{
  "user_id": "user_123",
  "streaks": [
    {
      "type": "food_logging",
      "current": 7,
      "best": 12
    }
  ]
}
```

#### Get Achievements

```http
GET /api/v1/users/{user_id}/achievements
```

**Response:**
```json
{
  "user_id": "user_123",
  "unlocked": [
    {
      "id": "first_week",
      "name": "Week Warrior",
      "description": "Logged food for 7 days straight"
    }
  ],
  "locked": [...]
}
```

---

## Rate Limiting

- **100 requests per minute** per IP address
- Returns `429 Too Many Requests` when exceeded

## CORS

Configure allowed origins via `CORS_ORIGINS` environment variable:

```bash
CORS_ORIGINS=http://localhost:3000,https://app.example.com
```

## Error Responses

All errors follow this format:

```json
{
  "error": "Brief error message",
  "detail": "Detailed explanation (optional)",
  "timestamp": "2025-12-22T12:00:00"
}
```

**Status Codes:**
- `200` - Success
- `201` - Created
- `204` - No Content (success, no response body)
- `400` - Bad Request (invalid input)
- `401` - Unauthorized (invalid API key)
- `403` - Forbidden (missing API key)
- `404` - Not Found (user/resource not found)
- `429` - Too Many Requests (rate limited)
- `500` - Internal Server Error

---

## Testing

### Automated Tests

```bash
# Run pytest tests
pytest tests/api/

# Specific test file
pytest tests/api/test_memory.py
```

### Manual Testing

```bash
# Run manual test suite
python scripts/test_api.py

# Run SCAR test suite
python scripts/scar_test_agent.py
```

### Example Test: Memory Retention

```python
import httpx
import asyncio

async def test_memory():
    async with httpx.AsyncClient(base_url="http://localhost:8080") as client:
        headers = {"Authorization": "Bearer test_key_123"}

        # 1. Create user
        await client.post("/api/v1/users", json={"user_id": "test"}, headers=headers)

        # 2. Tell agent something
        await client.post("/api/v1/chat", json={
            "user_id": "test",
            "message": "I love pizza"
        }, headers=headers)

        # 3. Clear conversation
        await client.delete("/api/v1/users/test/conversation", headers=headers)

        # 4. Ask agent to recall
        resp = await client.post("/api/v1/chat", json={
            "user_id": "test",
            "message": "What's my favorite food?"
        }, headers=headers)

        # Should remember "pizza"
        assert "pizza" in resp.json()["response"].lower()
        print("✅ Memory retention works!")

asyncio.run(test_memory())
```

---

## Docker Deployment

### Run API Server Only

```yaml
# docker-compose.yml
services:
  health-agent-api:
    build: .
    environment:
      RUN_MODE: api
      API_PORT: 8080
    env_file: .env
    ports:
      - "8080:8080"
```

```bash
docker-compose up health-agent-api
```

### Run Both Bot and API

```yaml
services:
  health-agent-bot:
    build: .
    environment:
      RUN_MODE: bot

  health-agent-api:
    build: .
    environment:
      RUN_MODE: api
    ports:
      - "8080:8080"
```

```bash
docker-compose up
```

---

## OpenAPI Documentation

FastAPI automatically generates interactive API documentation:

- **Swagger UI:** http://localhost:8080/docs
- **ReDoc:** http://localhost:8080/redoc
- **OpenAPI JSON:** http://localhost:8080/openapi.json

---

## Integration Examples

### SCAR (System Coding Agent Remote)

```python
# SCAR can now test the agent programmatically
async def scar_test():
    async with httpx.AsyncClient() as client:
        # Test memory retention
        await test_memory_retention(client)

        # Test reminders
        await test_reminder_scheduling(client)

        # Test gamification
        await test_xp_system(client)
```

### Project Orchestrator (PO)

```python
# PO can run tests and monitor agent health
async def po_health_check():
    resp = await client.get("http://localhost:8080/api/health")
    if resp.json()["status"] != "healthy":
        alert_admin("Agent API is down!")
```

### Web UI

```javascript
// Frontend can interact with agent
const response = await fetch('http://localhost:8080/api/v1/chat', {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer api_key',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    user_id: 'web_user_123',
    message: 'What should I eat for lunch?'
  })
});

const data = await response.json();
console.log(data.response);
```

---

## Security Considerations

- ✅ API keys stored in environment variables
- ✅ Rate limiting to prevent abuse
- ✅ Input validation on all endpoints
- ✅ SQL injection protection (parameterized queries)
- ✅ CORS properly configured
- ⚠️ **Use HTTPS in production**
- ⚠️ **Rotate API keys regularly**
- ⚠️ **Don't commit API keys to git**

---

## Troubleshooting

### API Not Starting

```bash
# Check if port is already in use
lsof -i :8080

# Check logs
RUN_MODE=api python src/main.py
```

### Database Connection Error

```bash
# Verify PostgreSQL is running
docker-compose ps postgres

# Check DATABASE_URL in .env
echo $DATABASE_URL
```

### Authentication Failing

```bash
# Verify API_KEYS in .env
echo $API_KEYS

# Test with correct header
curl -H "Authorization: Bearer test_key_123" http://localhost:8080/api/health
```

---

## Next Steps

1. **Production Deployment:**
   - Set up HTTPS (nginx reverse proxy)
   - Use strong API keys
   - Enable logging and monitoring

2. **Additional Features:**
   - WebSocket support for real-time updates
   - Batch operations
   - Data export/import
   - Admin API endpoints

3. **Documentation:**
   - Add more code examples
   - Create Postman collection
   - Video tutorials

---

## Support

For issues, questions, or feature requests:
- GitHub Issues: Create an issue with the `api` label
- Documentation: See main README.md

---

**Built with FastAPI, PostgreSQL, and PydanticAI**
