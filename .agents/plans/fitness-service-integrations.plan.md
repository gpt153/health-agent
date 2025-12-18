# Implementation Plan: Fitness Service Integrations

## Executive Summary

Integration with fitness services (Google Fitness, Mi Fit, etc.) to retrieve user health data (sleep, movement, training, weight) is **moderately complex** but highly feasible. The primary challenge is the **fragmented landscape** of fitness APIs and **recent platform deprecations**.

**Recommended Approach**: Use a unified health data aggregator (Terra, Thryve, or ROOK) rather than direct API integrations.

**Estimated Complexity**: 6/10
**Estimated Timeline**: 2-3 weeks for MVP with unified aggregator, 6-8 weeks for direct integrations

---

## Current Landscape Analysis

### Platform Status (2025)

#### Google Fit - ⚠️ DEPRECATED
- **Status**: Google Fit APIs officially deprecated as of July 1, 2025
- **Replacement**: Health Connect (Android framework integration)
- **Migration deadline**: Support ends June 30, 2025
- **Data available**: Steps, sleep, heart rate, activity sessions, calories, weight
- **Source**: [Google Fit Platform Overview](https://developers.google.com/fit/overview)

#### Health Connect - ✅ RECOMMENDED (Android)
- **Status**: Active, part of Android 14+ framework
- **Architecture**: Device-centric (local storage, no cloud API)
- **Authentication**: Built-in permission system (NOT OAuth-based)
- **Compatibility**: Android SDK 28+ (Pie and higher)
- **Data types**: 100+ fitness metrics including sleep stages, steps, heart rate, weight, workouts
- **Integration**: Requires Android app or third-party aggregator
- **Source**: [Health Connect Documentation](https://developer.android.com/health-and-fitness/health-connect)

#### Apple HealthKit - ✅ ACTIVE (iOS)
- **Status**: Active, industry standard for iOS
- **Architecture**: Local device storage only, encrypted
- **API**: No public cloud API available
- **Authentication**: iOS-native permission system
- **Data types**: Fitness, wellness, clinical/medical data
- **Integration**: Requires iOS app or third-party aggregator
- **Source**: [HealthKit Comparison](https://www.diversido.io/blog/how-apples-healthkit-and-google-fit-apis-help-in-health-and-fitness-apps-development)

#### Xiaomi Mi Fit / Mi Fitness - ⚠️ FRAGMENTED
- **Status**: No official public API
- **Ecosystem**: Fragmented across Mi Fit, Mi Fitness, Zepp Life apps
- **Integration methods**:
  1. Via Health Connect (Android) - users connect Xiaomi account to Health Connect
  2. Via Apple Health (iOS) - one-time connection of Xiaomi account to Apple Health
  3. Third-party aggregators (Thryve, ROOK, Terra)
- **Data sync**: Available via Google Fit integration (deprecated) or platform APIs
- **Source**: [ROOK Mi Fitness Documentation](https://docs.tryrook.io/data-sources/xiaomi/)

### Key Challenges

1. **Platform Fragmentation**: Each platform has different APIs, data structures, and permission models
2. **No Cloud APIs**: Health Connect and Apple HealthKit are device-only (no REST APIs)
3. **Authentication Complexity**: OAuth for some, platform permissions for others
4. **Deprecation Risk**: Google Fit deprecated, requiring migration strategies
5. **Regional Variations**: Different devices/services popular in different regions
6. **Data Normalization**: Each platform structures data differently

---

## Architecture Options

### Option 1: Unified API Aggregator (RECOMMENDED) ⭐

**Use a third-party health data aggregator service**

#### Available Providers

| Provider | Coverage | Regions | Compliance | Best For |
|----------|----------|---------|------------|----------|
| **Terra** | 500+ devices | Global | GDPR, HIPAA | Startups, MVPs, no-code |
| **Thryve** | 500+ devices | Europe-focused | GDPR, HIPAA, ISO 27001 | European healthcare |
| **ROOK** | Major platforms | Global | FHIR-compliant | Health insights, personalization |

**Sources**:
- [Thryve Platform](https://www.thryve.health/)
- [ROOK Wearable API](https://www.tryrook.io/wearable-api-sdk)
- [Terra Comparison](https://www.producthunt.com/products/terra-2/alternatives)

#### How It Works

```
User Device (Mi Fit/Google Fit/Apple Health)
            ↓
    Platform APIs (Health Connect/HealthKit)
            ↓
    Aggregator Service (Terra/Thryve/ROOK)
            ↓ (Webhook or REST API)
    Health Agent Backend
            ↓
    User's Telegram Bot
```

#### Pros
- ✅ Single integration point for 500+ devices
- ✅ Handles OAuth, permissions, data normalization
- ✅ Manages platform deprecations and updates
- ✅ GDPR/HIPAA compliant
- ✅ Webhook-based real-time updates
- ✅ Consistent data format across all sources
- ✅ Fast implementation (1-2 weeks)

#### Cons
- ❌ Monthly subscription cost ($99-$499/month typical)
- ❌ External dependency
- ❌ Data routed through third party
- ❌ Less control over data flow

#### Cost Estimates
- **Terra**: ~$99-299/month (startup tier)
- **Thryve**: Custom pricing, GDPR-focused
- **ROOK**: Custom pricing, health insights included

---

### Option 2: Direct Platform Integrations

**Build direct integrations with each platform**

#### Required Integrations

1. **Health Connect (Android)**
   - Requires Android SDK integration
   - Need companion Android app OR web OAuth flow (limited)
   - Can't directly access from Python backend

2. **Apple HealthKit (iOS)**
   - Requires iOS SDK integration
   - Need companion iOS app
   - No cloud/REST API available

3. **Fitbit Web API**
   - REST API available
   - OAuth 2.0 authentication
   - Accessible from Python backend ✅

4. **Garmin Connect API**
   - REST API available (requires partnership)
   - OAuth 1.0a authentication
   - Limited public access

#### Architecture

```
┌─────────────────────────────────────────┐
│     Health Agent (Telegram Bot)         │
│         Python/PostgreSQL                │
└──────────────┬──────────────────────────┘
               │
        ┌──────┴──────────────────┐
        │                         │
   REST APIs              Mobile App Companion
   (Fitbit, etc.)         (Android/iOS)
        │                         │
        │                  ┌──────┴─────────┐
        │                  │                │
        │            Health Connect   HealthKit
        │              (Android)       (iOS)
        │                  │                │
        └──────────────────┴────────────────┴────
               User's Wearable Data
```

#### Pros
- ✅ Full control over data flow
- ✅ No recurring subscription costs
- ✅ Direct platform relationships
- ✅ Can optimize for specific use cases

#### Cons
- ❌ Need to build iOS + Android companion apps
- ❌ Complex OAuth flows for multiple platforms
- ❌ Maintain separate integrations (5+ platforms)
- ❌ Handle platform deprecations manually (Google Fit → Health Connect)
- ❌ Data normalization complexity
- ❌ Long development time (6-8 weeks minimum)
- ❌ Mobile app development required

---

### Option 3: Hybrid Approach

**Use aggregator for mobile platforms + direct REST APIs for cloud services**

#### Integration Strategy

1. **Aggregator** (Terra/Thryve/ROOK): Health Connect, Apple HealthKit, Mi Fit
2. **Direct REST APIs**: Fitbit, Garmin (if partnership available), Oura

#### Pros
- ✅ No mobile app development needed
- ✅ Direct control for REST API services
- ✅ Aggregator handles mobile complexity
- ⚡ Balanced cost vs. control

#### Cons
- ⚠️ Still requires aggregator subscription
- ⚠️ Two integration patterns to maintain

---

## Recommended Implementation Plan

### Phase 1: MVP with Unified Aggregator (Week 1-2)

**Choose**: **Terra API** (best for startups/MVPs)

#### Week 1: Infrastructure Setup

**1.1 Database Schema Extension**
```sql
-- Add to migrations/004_fitness_integrations.sql

CREATE TABLE fitness_connections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    provider VARCHAR(50) NOT NULL,           -- 'terra', 'fitbit', etc.
    provider_user_id VARCHAR(255),
    access_token_encrypted TEXT,             -- Encrypted OAuth token
    refresh_token_encrypted TEXT,
    token_expires_at TIMESTAMP,
    scopes JSONB,                            -- Granted permissions
    connected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_sync_at TIMESTAMP,
    active BOOLEAN DEFAULT true,
    UNIQUE(user_id, provider)
);

CREATE TABLE fitness_data (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    connection_id UUID REFERENCES fitness_connections(id) ON DELETE CASCADE,
    data_type VARCHAR(50) NOT NULL,          -- 'sleep', 'steps', 'weight', 'workout'
    timestamp TIMESTAMP NOT NULL,            -- When data was recorded
    data JSONB NOT NULL,                     -- Normalized fitness data
    raw_data JSONB,                          -- Original provider data
    synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_fitness_data_user_type_time (user_id, data_type, timestamp DESC)
);
```

**1.2 Environment Configuration**
```bash
# Add to .env
TERRA_API_KEY=your_terra_api_key
TERRA_DEV_ID=your_terra_dev_id
TERRA_WEBHOOK_SECRET=your_webhook_secret
FITNESS_WEBHOOK_URL=https://your-domain.com/webhooks/fitness
```

**1.3 Dependencies**
```toml
# Add to pyproject.toml
dependencies = [
    # ... existing deps
    "httpx>=0.27.0",           # Async HTTP client
    "cryptography>=42.0.0",    # Token encryption
]
```

#### Week 2: Core Integration

**2.1 Terra API Client** (`src/integrations/terra_client.py`)
- OAuth connection flow
- Webhook handling
- Data retrieval methods
- Error handling

**2.2 Telegram Flow** (`src/handlers/fitness_connect.py`)
- `/connect_fitness` command
- Device selection UI (inline keyboard)
- OAuth redirect handling
- Connection status display

**2.3 Data Sync Service** (`src/services/fitness_sync.py`)
- Webhook receiver
- Data normalization
- Storage to database
- User notifications

**2.4 Agent Tool Integration** (`src/agent/fitness_tools.py`)
- PydanticAI tools for querying fitness data
- Natural language queries: "How did I sleep last night?"
- Insights generation

#### Deliverables
- ✅ Users can connect Google Fit, Apple Health, Mi Fit, Fitbit via Telegram
- ✅ Automatic data sync via webhooks
- ✅ Query data through chat: "What was my average sleep this week?"
- ✅ Data stored securely in PostgreSQL

---

### Phase 2: Data Insights & Coaching (Week 3-4)

**2.1 Sleep Analysis**
- Sleep quality scoring
- Pattern detection (consistency, duration)
- Recommendations based on sleep data

**2.2 Activity Tracking**
- Daily step goals
- Workout summaries
- Sedentary time alerts

**2.3 Weight Tracking**
- Trend visualization (via text)
- Progress toward goals
- Correlation with activity/nutrition

**2.4 Holistic Coaching**
- Correlate fitness data with food logs
- Personalized recommendations
- Proactive check-ins based on patterns

#### Example Agent Interaction
```
User: "How did I sleep last night?"

Agent: "🌙 Last night's sleep:
• Duration: 7h 23m
• Deep sleep: 1h 42m (good!)
• REM: 1h 18m
• Sleep score: 78/100

You went to bed at 23:15 (15 min later than usual).
Your deep sleep was excellent - likely because you
trained yesterday and hit your protein target.

💡 Try to get to bed by 23:00 tonight to reach your
8-hour goal."
```

---

### Phase 3: Advanced Features (Optional)

**3.1 Multi-Device Support**
- Handle users with multiple wearables
- Conflict resolution (which device to trust)
- Device priority settings

**3.2 Historical Data Import**
- Backfill past data on connection
- Bulk import flows

**3.3 Custom Metrics**
- HRV (Heart Rate Variability)
- VO2 max
- Training load/readiness

**3.4 Export & Privacy**
- Data export (GDPR compliance)
- Connection management
- Granular data deletion

---

## Technical Implementation Details

### OAuth Flow (Terra Example)

```python
# src/integrations/terra_client.py

import httpx
from typing import Optional

class TerraClient:
    BASE_URL = "https://api.tryterra.co/v2"

    async def generate_auth_url(self, user_id: str, provider: str) -> str:
        """Generate OAuth URL for user to connect device"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.BASE_URL}/auth/generateWidgetSession",
                headers={
                    "dev-id": self.dev_id,
                    "x-api-key": self.api_key
                },
                json={
                    "reference_id": user_id,
                    "providers": [provider],  # "GOOGLE", "APPLE", "FITBIT", etc.
                    "auth_success_redirect_url": f"{self.callback_url}/success",
                    "auth_failure_redirect_url": f"{self.callback_url}/failure"
                }
            )
            data = response.json()
            return data["url"]

    async def get_sleep_data(self, user_id: str, start_date: str, end_date: str) -> dict:
        """Retrieve sleep data for user"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/sleep",
                headers={
                    "dev-id": self.dev_id,
                    "x-api-key": self.api_key
                },
                params={
                    "user_id": user_id,
                    "start_date": start_date,
                    "end_date": end_date
                }
            )
            return response.json()
```

### Telegram Handler

```python
# src/handlers/fitness_connect.py

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

async def connect_fitness(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /connect_fitness command"""
    user_id = str(update.effective_user.id)

    # Show provider selection
    keyboard = [
        [InlineKeyboardButton("Google Fit", callback_data="connect:google")],
        [InlineKeyboardButton("Apple Health", callback_data="connect:apple")],
        [InlineKeyboardButton("Mi Fit", callback_data="connect:xiaomi")],
        [InlineKeyboardButton("Fitbit", callback_data="connect:fitbit")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "🏃‍♂️ Connect your fitness device:\n\n"
        "This will allow me to access your:\n"
        "• Sleep data (duration, quality, stages)\n"
        "• Activity (steps, workouts, calories)\n"
        "• Body metrics (weight, heart rate)\n\n"
        "Select your device/app:",
        reply_markup=reply_markup
    )

async def handle_connect_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle provider selection"""
    query = update.callback_query
    await query.answer()

    provider = query.data.split(":")[1]  # "connect:google" → "google"
    user_id = str(query.from_user.id)

    # Generate OAuth URL
    auth_url = await terra_client.generate_auth_url(user_id, provider.upper())

    await query.edit_message_text(
        f"🔗 Connect your {provider.title()} account:\n\n"
        f"Click the link below to authorize access:\n{auth_url}\n\n"
        f"After connecting, I'll automatically sync your health data!"
    )
```

### Webhook Handler

```python
# src/handlers/webhooks.py

from fastapi import FastAPI, Request, HTTPException
from src.integrations.terra_client import verify_webhook_signature

app = FastAPI()

@app.post("/webhooks/fitness/terra")
async def terra_webhook(request: Request):
    """Handle Terra webhook notifications"""
    body = await request.body()
    signature = request.headers.get("terra-signature")

    # Verify webhook authenticity
    if not verify_webhook_signature(body, signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

    data = await request.json()

    # Handle different event types
    if data["type"] == "sleep":
        await process_sleep_data(data["user_id"], data["data"])
    elif data["type"] == "activity":
        await process_activity_data(data["user_id"], data["data"])
    elif data["type"] == "body":
        await process_body_data(data["user_id"], data["data"])

    return {"status": "ok"}
```

### Data Normalization

```python
# src/services/fitness_normalizer.py

from pydantic import BaseModel
from datetime import datetime

class NormalizedSleepData(BaseModel):
    """Standardized sleep data format"""
    user_id: str
    date: datetime
    duration_minutes: int
    deep_sleep_minutes: int
    light_sleep_minutes: int
    rem_sleep_minutes: int
    awake_minutes: int
    sleep_score: Optional[int]  # 0-100
    bedtime: datetime
    wakeup_time: datetime
    source: str  # "google_fit", "apple_health", "fitbit"

def normalize_terra_sleep(raw_data: dict) -> NormalizedSleepData:
    """Convert Terra API sleep data to normalized format"""
    sleep = raw_data["sleep"]
    return NormalizedSleepData(
        user_id=raw_data["user"]["user_id"],
        date=datetime.fromisoformat(sleep["day"]),
        duration_minutes=sleep["duration_asleep_state_seconds"] // 60,
        deep_sleep_minutes=sleep["duration_deep_sleep_state_seconds"] // 60,
        light_sleep_minutes=sleep["duration_light_sleep_state_seconds"] // 60,
        rem_sleep_minutes=sleep["duration_REM_sleep_state_seconds"] // 60,
        awake_minutes=sleep["duration_awake_state_seconds"] // 60,
        sleep_score=sleep.get("score"),
        bedtime=datetime.fromisoformat(sleep["bedtime_start"]),
        wakeup_time=datetime.fromisoformat(sleep["bedtime_stop"]),
        source="terra"
    )
```

---

## Security & Privacy Considerations

### 1. Token Encryption
```python
from cryptography.fernet import Fernet

class TokenEncryption:
    def __init__(self, key: bytes):
        self.cipher = Fernet(key)

    def encrypt_token(self, token: str) -> str:
        return self.cipher.encrypt(token.encode()).decode()

    def decrypt_token(self, encrypted: str) -> str:
        return self.cipher.decrypt(encrypted.encode()).decode()
```

### 2. GDPR Compliance
- ✅ User consent before connection
- ✅ Data retention policies (auto-delete after X days)
- ✅ User-initiated data deletion
- ✅ Export functionality
- ✅ Clear privacy policy

### 3. Data Minimization
- Only request necessary scopes
- Store aggregated data when possible
- Implement data retention limits

### 4. Audit Trail
```sql
CREATE TABLE fitness_audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL,
    action VARCHAR(50) NOT NULL,  -- 'connect', 'sync', 'disconnect', 'delete'
    provider VARCHAR(50),
    details JSONB,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## Cost Analysis

### Option 1: Unified Aggregator (Terra)

| Component | Cost | Notes |
|-----------|------|-------|
| Terra API | $99-299/month | Startup tier, 1000 users |
| Development | 2 weeks | Internal dev cost |
| Maintenance | 4 hrs/month | Minimal ongoing work |
| **Total Year 1** | **$1,200-3,600** | Subscription only |

**Break-even**: ~50-100 users to justify subscription

### Option 2: Direct Integrations

| Component | Cost | Notes |
|-----------|------|-------|
| iOS Developer | $99/year | Apple Developer Program |
| Android | Free | Google Play Console |
| Development | 6-8 weeks | Backend + 2 mobile apps |
| Maintenance | 20 hrs/month | Platform updates, OAuth refresh |
| **Total Year 1** | **$100 + dev time** | Much higher dev cost |

**Break-even**: Only worthwhile if handling deprecations/updates in-house

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Platform deprecation (like Google Fit) | High | High | Use aggregator to handle transitions |
| OAuth token expiration | Medium | Medium | Implement refresh token flow |
| Data sync delays | Medium | Low | Set user expectations, show last sync time |
| Aggregator service outage | Low | Medium | Cache critical data, fallback messages |
| Privacy/GDPR violations | Low | Critical | Regular audits, encrypt all tokens |

---

## Recommendation Summary

### ✅ RECOMMENDED: **Option 1 - Unified Aggregator (Terra API)**

**Why:**
1. **Fastest time to market**: 2 weeks vs 8 weeks
2. **Future-proof**: Aggregator handles platform changes (Google Fit deprecation)
3. **No mobile app required**: Works through existing platform apps
4. **Comprehensive coverage**: 500+ devices from one integration
5. **Maintenance**: Minimal ongoing work
6. **User experience**: Seamless connection flow

**When to choose direct integrations:**
- You need custom data processing not offered by aggregators
- You have 1000+ users (break-even on cost)
- You have dedicated mobile dev team
- You need real-time data (< 1 minute latency)

### Implementation Phases

1. **Phase 1 (Week 1-2)**: Terra integration MVP
   - Users can connect devices
   - Sleep, steps, weight data syncing
   - Basic querying through chat

2. **Phase 2 (Week 3-4)**: Insights & coaching
   - Sleep quality analysis
   - Activity recommendations
   - Weight trend tracking
   - Correlation with food logs

3. **Phase 3 (Future)**: Advanced features
   - Multi-device support
   - HRV, VO2 max metrics
   - Custom goals & alerts

---

## Next Steps

1. **Choose aggregator provider**: Evaluate Terra vs Thryve vs ROOK demos
2. **Sign up for API access**: Terra has free developer tier
3. **Set up test account**: Connect personal fitness device
4. **Implement Phase 1**: Follow technical plan above
5. **User testing**: Test with 5-10 early users
6. **Iterate based on feedback**: Refine data insights

---

## References & Sources

### Platform Documentation
- [Google Fit Platform Overview](https://developers.google.com/fit/overview)
- [Health Connect Documentation](https://developer.android.com/health-and-fitness/health-connect)
- [Health Connect Integration Guide](https://developer.android.com/codelabs/health-connect)
- [HealthKit vs Google Fit Comparison](https://www.diversido.io/blog/how-apples-healthkit-and-google-fit-apis-help-in-health-and-fitness-apps-development)
- [Wearable Data Integration Guide](https://llif.org/2025/04/28/how-to-integrate-health-data-from-wearables-apple-health-fitbit-google-fit/)

### API Aggregators
- [Thryve Platform](https://www.thryve.health/)
- [ROOK Wearable API](https://www.tryrook.io/wearable-api-sdk)
- [Terra API Alternatives](https://www.producthunt.com/products/terra-2/alternatives)
- [ROOK vs Competitors](https://www.tryrook.io/blog/rook-vs-other-offerings-why-digital-health-companies-choosenbsprook)

### Mi Fit Integration
- [ROOK Mi Fitness Documentation](https://docs.tryrook.io/data-sources/xiaomi/)
- [Thryve Xiaomi Integration](https://www.thryve.health/features/connections/xiaomi-mi-fit-integration)
- [Google Fit Integration Guide](https://lifetrails.ai/blog/google-fit-integration-guide)

### Technical Resources
- [Google Fit API Deprecation Notice](https://www.thryve.health/blog/google-fit-api-deprecation-and-the-new-health-connect-by-android-what-thryve-customers-need-to-know)
- [Health Connect Comparison Guide](https://developer.android.com/health-and-fitness/health-connect/comparison-guide)
- [Read Sleep Data with Google Fit](https://developers.google.com/fit/scenarios/read-sleep-data)

---

## Appendix: Data Types Available

### Sleep Data
- Total duration
- Sleep stages (deep, light, REM, awake)
- Sleep quality score
- Bedtime/wake time
- Heart rate during sleep
- Respiratory rate
- Sleep interruptions

### Activity Data
- Steps (daily, hourly)
- Distance traveled
- Active minutes
- Calories burned
- Exercise sessions (type, duration, intensity)
- Heart rate zones
- Workout summaries

### Body Metrics
- Weight
- Body fat percentage
- BMI
- Heart rate (resting, active)
- Blood pressure (if device supports)
- Oxygen saturation (SpO2)

### Training Data
- Workout type
- Duration
- Calories burned
- Average/max heart rate
- Training load
- Recovery time
- VO2 max estimate

---

**Plan Status**: Ready for approval
**Next Action**: User decision on aggregator vs direct integration approach
