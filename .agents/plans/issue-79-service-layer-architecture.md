# Issue #79: Service Layer Architecture Implementation

**Epic**: Phase 3.3 - Long-Term Architecture
**Priority**: HIGH
**Estimated Time**: 16 hours
**Status**: PLANNED

## Executive Summary

This plan implements a clean service layer architecture to separate business logic from bot handlers and database operations, improving testability, maintainability, and code reuse across the health agent application.

## Current State Analysis

### Architecture Problems
1. **Business Logic in Handlers**: Bot handlers (`bot.py`, `handlers/`) directly contain business logic mixed with Telegram-specific code
2. **Direct Database Coupling**: Handlers call `src.db.queries` functions directly, creating tight coupling
3. **Code Duplication**: Similar logic repeated across handlers (e.g., gamification, validation)
4. **Hard to Test**: Handler functions require mocking Telegram context objects
5. **No Reusability**: Business logic cannot be reused from API or CLI interfaces

### Current Structure
```
Telegram Bot Handlers (bot.py, handlers/)
    ↓ Direct calls
Database Queries (db/queries.py)
    ↓ Direct SQL
PostgreSQL Database
```

### Key Files Requiring Refactoring
- `src/bot.py` (1399 lines) - Massive bot file with embedded logic
- `src/handlers/onboarding.py` - Onboarding logic mixed with Telegram
- `src/handlers/reminders.py` - Reminder logic tightly coupled to handlers
- `src/agent/__init__.py` - Agent logic with database calls
- `src/gamification/integrations.py` - Gamification hooks with mixed concerns

## Target Architecture

### Layered Architecture
```
┌─────────────────────────────────────────────┐
│   Presentation Layer (Telegram Handlers)    │
│   - bot.py, handlers/*                      │
│   - Receives updates, formats responses     │
└─────────────────┬───────────────────────────┘
                  ↓
┌─────────────────────────────────────────────┐
│        Service Layer (NEW)                  │
│   - UserService                             │
│   - FoodService                             │
│   - GamificationService                     │
│   - HealthService                           │
│   - Business logic, validation, workflows   │
└─────────────────┬───────────────────────────┘
                  ↓
┌─────────────────────────────────────────────┐
│   Repository Layer (db/queries.py)          │
│   - Database queries                        │
│   - Data access only                        │
└─────────────────┬───────────────────────────┘
                  ↓
┌─────────────────────────────────────────────┐
│          PostgreSQL Database                │
└─────────────────────────────────────────────┘
```

## Service Layer Design

### 1. UserService Interface

**Responsibilities**:
- User lifecycle management (create, update, authenticate)
- Onboarding flow orchestration
- User preferences and settings management
- Subscription/activation handling

**Interface**:
```python
# src/services/user_service.py

from typing import Optional, Dict, Any
from datetime import datetime

class UserService:
    """Service for user management and preferences"""

    def __init__(self, db_connection):
        self.db = db_connection

    async def create_user(
        self,
        telegram_id: str
    ) -> Dict[str, Any]:
        """Create new user with default settings"""

    async def get_user(
        self,
        telegram_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get user by telegram ID"""

    async def activate_user(
        self,
        telegram_id: str,
        invite_code: str
    ) -> Dict[str, bool]:
        """Activate user with invite code"""

    async def is_authorized(
        self,
        telegram_id: str
    ) -> bool:
        """Check if user is authorized to use bot"""

    async def get_onboarding_state(
        self,
        telegram_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get current onboarding state"""

    async def update_onboarding_state(
        self,
        telegram_id: str,
        state: Dict[str, Any]
    ) -> bool:
        """Update onboarding progress"""

    async def complete_onboarding(
        self,
        telegram_id: str
    ) -> bool:
        """Mark onboarding as complete"""

    async def update_preferences(
        self,
        telegram_id: str,
        preferences: Dict[str, Any]
    ) -> bool:
        """Update user preferences"""

    async def get_subscription_status(
        self,
        telegram_id: str
    ) -> Dict[str, Any]:
        """Get user subscription details"""
```

### 2. FoodService Interface

**Responsibilities**:
- Food photo analysis coordination
- Nutrition calculation and validation
- Meal logging and retrieval
- Food entry corrections
- Integration with vision AI and USDA database

**Interface**:
```python
# src/services/food_service.py

from typing import List, Optional, Dict, Any
from datetime import datetime, date
from src.models.food import FoodEntry, VisionAnalysisResult

class FoodService:
    """Service for food tracking and analysis"""

    def __init__(self, db_connection, memory_manager):
        self.db = db_connection
        self.memory = memory_manager

    async def analyze_food_photo(
        self,
        user_id: str,
        photo_path: str,
        caption: Optional[str] = None
    ) -> VisionAnalysisResult:
        """
        Analyze food photo with personalization
        - Load user visual patterns
        - Search semantic memory (Mem0)
        - Apply food habits
        - Run vision AI analysis
        - Validate with USDA database
        """

    async def log_food_entry(
        self,
        user_id: str,
        food_entry: FoodEntry
    ) -> Dict[str, Any]:
        """
        Save food entry to database
        - Validate entry
        - Save to database
        - Trigger habit detection
        - Return entry with ID
        """

    async def get_food_entries(
        self,
        user_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 10
    ) -> List[FoodEntry]:
        """Get food entries for date range"""

    async def correct_food_entry(
        self,
        user_id: str,
        entry_id: str,
        corrections: Dict[str, Any],
        note: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Correct an existing food entry
        - Validate ownership
        - Update entry
        - Log to audit table
        """

    async def get_daily_nutrition_summary(
        self,
        user_id: str,
        target_date: date
    ) -> Dict[str, Any]:
        """Calculate nutrition totals for a day"""

    async def get_weekly_patterns(
        self,
        user_id: str
    ) -> Dict[str, Any]:
        """Analyze weekly eating patterns"""
```

### 3. GamificationService Interface

**Responsibilities**:
- XP calculation and awarding
- Streak tracking and updates
- Achievement checking and unlocking
- Leaderboard management
- Motivation profile integration

**Interface**:
```python
# src/services/gamification_service.py

from typing import Dict, List, Any
from datetime import datetime

class GamificationService:
    """Service for gamification features"""

    def __init__(self, db_connection):
        self.db = db_connection

    async def award_xp(
        self,
        user_id: str,
        amount: int,
        source_type: str,  # "food_entry", "reminder", "tracking"
        source_id: str,
        reason: str
    ) -> Dict[str, Any]:
        """
        Award XP to user
        - Calculate bonuses (streaks, timing)
        - Update user XP
        - Check for level up
        - Return XP result with level info
        """

    async def update_streak(
        self,
        user_id: str,
        streak_type: str,  # "food_logging", "reminder"
        action_date: datetime
    ) -> Dict[str, Any]:
        """
        Update streak for activity
        - Load current streak
        - Check if streak continues
        - Update or reset streak
        - Return streak info
        """

    async def check_achievements(
        self,
        user_id: str,
        trigger_type: str,
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Check for newly unlocked achievements
        - Load user progress
        - Evaluate achievement conditions
        - Unlock and save achievements
        - Return list of unlocked achievements
        """

    async def process_food_entry_gamification(
        self,
        user_id: str,
        food_entry_id: str,
        logged_at: datetime,
        meal_type: str
    ) -> Dict[str, Any]:
        """
        Complete gamification flow for food entry
        - Award XP
        - Update streak
        - Check achievements
        - Return combined result with message
        """

    async def process_reminder_completion_gamification(
        self,
        user_id: str,
        reminder_id: str,
        completed_at: datetime,
        scheduled_time: str
    ) -> Dict[str, Any]:
        """Complete gamification flow for reminder"""

    async def process_tracking_entry_gamification(
        self,
        user_id: str,
        tracking_entry_id: str,
        category_name: str,
        logged_at: datetime
    ) -> Dict[str, Any]:
        """Complete gamification flow for tracking entry"""

    async def get_user_stats(
        self,
        user_id: str
    ) -> Dict[str, Any]:
        """Get user's gamification stats (XP, level, streaks, achievements)"""

    async def get_leaderboard(
        self,
        leaderboard_type: str = "xp",
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get leaderboard rankings"""
```

### 4. HealthService Interface

**Responsibilities**:
- Health metric tracking (weight, steps, sleep)
- Trend analysis and calculations
- Health report generation
- Custom tracking categories
- Reminder management

**Interface**:
```python
# src/services/health_service.py

from typing import List, Optional, Dict, Any
from datetime import datetime, date
from src.models.tracking import TrackingCategory, TrackingEntry
from src.models.reminder import Reminder

class HealthService:
    """Service for health tracking and insights"""

    def __init__(self, db_connection, memory_manager, reminder_manager=None):
        self.db = db_connection
        self.memory = memory_manager
        self.reminder_manager = reminder_manager

    # Tracking Categories
    async def create_tracking_category(
        self,
        user_id: str,
        category: TrackingCategory
    ) -> Dict[str, Any]:
        """Create new tracking category"""

    async def get_tracking_categories(
        self,
        user_id: str,
        active_only: bool = True
    ) -> List[TrackingCategory]:
        """Get user's tracking categories"""

    async def deactivate_tracking_category(
        self,
        user_id: str,
        category_id: str
    ) -> bool:
        """Deactivate a tracking category"""

    # Tracking Entries
    async def log_tracking_entry(
        self,
        user_id: str,
        entry: TrackingEntry
    ) -> Dict[str, Any]:
        """
        Log tracking entry
        - Validate category exists
        - Save entry
        - Trigger gamification
        - Return entry with ID
        """

    async def get_tracking_entries(
        self,
        user_id: str,
        category_id: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 50
    ) -> List[TrackingEntry]:
        """Get tracking entries for category and date range"""

    # Reminders
    async def create_reminder(
        self,
        user_id: str,
        reminder: Reminder
    ) -> Dict[str, Any]:
        """
        Create and schedule reminder
        - Save to database
        - Schedule with reminder_manager
        - Return reminder info
        """

    async def get_reminders(
        self,
        user_id: str,
        active_only: bool = True
    ) -> List[Reminder]:
        """Get user's reminders"""

    async def cancel_reminder(
        self,
        user_id: str,
        reminder_id: str
    ) -> bool:
        """
        Cancel a reminder
        - Deactivate in database
        - Unschedule from reminder_manager
        """

    async def complete_reminder(
        self,
        user_id: str,
        reminder_id: str,
        completed_at: datetime,
        note: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Mark reminder as completed
        - Save completion record
        - Trigger gamification
        - Return result
        """

    # Health Insights
    async def calculate_trends(
        self,
        user_id: str,
        metric_type: str,  # "weight", "sleep", custom category
        days: int = 7
    ) -> Dict[str, Any]:
        """
        Calculate trends for a metric
        - Load entries
        - Calculate average, min, max, trend direction
        - Return trend analysis
        """

    async def generate_health_report(
        self,
        user_id: str,
        start_date: date,
        end_date: date
    ) -> Dict[str, Any]:
        """
        Generate comprehensive health report
        - Food summary
        - Tracking summary
        - Achievements
        - Streaks
        - Trends
        """

    async def detect_anomalies(
        self,
        user_id: str,
        metric_type: str
    ) -> List[Dict[str, Any]]:
        """Detect unusual patterns in health metrics"""
```

## Dependency Injection Strategy

### Simple Service Container

**Approach**: Use a simple dependency injection container instead of a heavy framework.

**Implementation**:
```python
# src/services/container.py

from dataclasses import dataclass
from typing import Optional
from src.db.connection import DatabaseConnection
from src.memory.file_manager import MemoryFileManager
from src.services.user_service import UserService
from src.services.food_service import FoodService
from src.services.gamification_service import GamificationService
from src.services.health_service import HealthService

@dataclass
class ServiceContainer:
    """Simple dependency injection container for services"""

    # Infrastructure
    db: DatabaseConnection
    memory_manager: MemoryFileManager
    reminder_manager: Optional[object] = None  # Set after bot creation

    # Services (lazy-loaded)
    _user_service: Optional[UserService] = None
    _food_service: Optional[FoodService] = None
    _gamification_service: Optional[GamificationService] = None
    _health_service: Optional[HealthService] = None

    @property
    def user_service(self) -> UserService:
        if self._user_service is None:
            self._user_service = UserService(self.db)
        return self._user_service

    @property
    def food_service(self) -> FoodService:
        if self._food_service is None:
            self._food_service = FoodService(self.db, self.memory_manager)
        return self._food_service

    @property
    def gamification_service(self) -> GamificationService:
        if self._gamification_service is None:
            self._gamification_service = GamificationService(self.db)
        return self._gamification_service

    @property
    def health_service(self) -> HealthService:
        if self._health_service is None:
            self._health_service = HealthService(
                self.db,
                self.memory_manager,
                self.reminder_manager
            )
        return self._health_service


# Global container instance (initialized in main.py)
_container: Optional[ServiceContainer] = None

def get_container() -> ServiceContainer:
    """Get global service container"""
    if _container is None:
        raise RuntimeError("Service container not initialized")
    return _container

def init_container(
    db: DatabaseConnection,
    memory_manager: MemoryFileManager,
    reminder_manager: Optional[object] = None
) -> ServiceContainer:
    """Initialize global service container"""
    global _container
    _container = ServiceContainer(
        db=db,
        memory_manager=memory_manager,
        reminder_manager=reminder_manager
    )
    return _container
```

### Integration in main.py

```python
# src/main.py (updated)

from src.services.container import init_container, get_container

async def main():
    # ... existing setup ...

    await db.init_pool()

    # Initialize service container AFTER db and memory
    container = init_container(
        db=db,
        memory_manager=memory_manager
    )

    # Create bot (will set reminder_manager in container later)
    app = create_bot_application()

    # Update container with reminder_manager
    from src.bot import reminder_manager
    container.reminder_manager = reminder_manager

    # ... rest of setup ...
```

### Handler Integration Pattern

**Before** (Direct database calls):
```python
# src/handlers/onboarding.py (OLD)

from src.db.queries import create_user, get_onboarding_state

async def handle_onboarding_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)

    # Direct database call
    if not await user_exists(user_id):
        await create_user(user_id)

    # More direct calls...
```

**After** (Service layer):
```python
# src/handlers/onboarding.py (NEW)

from src.services.container import get_container

async def handle_onboarding_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    container = get_container()

    # Use service
    user = await container.user_service.get_user(user_id)
    if not user:
        await container.user_service.create_user(user_id)

    # Business logic in service, handler just coordinates
```

## Implementation Plan - Phased Approach

### Phase 1: Foundation & UserService (4 hours)

**Goal**: Set up service layer foundation and implement UserService

**Tasks**:
1. Create service directory structure
   ```
   src/services/
   ├── __init__.py
   ├── container.py         # DI container
   ├── user_service.py      # User management
   └── base_service.py      # Optional base class
   ```

2. Implement `ServiceContainer` with DI pattern
   - Simple property-based lazy loading
   - Initialize in `main.py`

3. Implement `UserService`
   - Extract user management logic from `bot.py`
   - Methods: create, get, activate, authorize, onboarding state
   - Unit tests: `tests/unit/test_user_service.py`

4. Refactor user-related handlers to use `UserService`
   - `bot.py`: start, activate, onboard commands
   - `handlers/onboarding.py`: onboarding flow

5. Update `main.py` to initialize container

**Acceptance Criteria**:
- ✅ UserService implemented with all methods
- ✅ Unit tests at 90%+ coverage
- ✅ Handlers use UserService (no direct db calls for users)
- ✅ All existing tests pass

### Phase 2: FoodService (5 hours)

**Goal**: Implement FoodService and refactor food photo handling

**Tasks**:
1. Implement `FoodService`
   - Extract food logic from `bot.py::handle_photo()`
   - Methods: analyze_photo, log_entry, get_entries, correct_entry, daily_summary
   - Integration with vision AI, USDA validation, habit detection

2. Refactor food photo handler
   - `bot.py::handle_photo()` → slim handler calling `FoodService`
   - Keep Telegram-specific code (replies, formatting) in handler
   - Move business logic to service

3. Refactor food entry corrections
   - Use `FoodService.correct_food_entry()`

4. Unit tests
   - `tests/unit/test_food_service.py`
   - Mock database and external APIs
   - Test analysis flow, validation, habit detection

5. Integration tests
   - `tests/integration/test_food_service_flow.py`
   - End-to-end food logging flow

**Acceptance Criteria**:
- ✅ FoodService implemented
- ✅ Food photo handler refactored (< 100 lines)
- ✅ Unit tests at 90%+ coverage
- ✅ Integration tests pass
- ✅ No database calls in `handle_photo()` handler

### Phase 3: GamificationService (3 hours)

**Goal**: Implement GamificationService and consolidate gamification logic

**Tasks**:
1. Implement `GamificationService`
   - Extract from `src/gamification/integrations.py`
   - Methods: award_xp, update_streak, check_achievements, process_* methods
   - Consolidate XP, streak, and achievement logic

2. Refactor gamification integrations
   - Update `gamification/integrations.py` to use service
   - Or deprecate integrations.py and call service directly

3. Update handlers to use `GamificationService`
   - Food handler: call service after logging
   - Reminder handler: call service after completion
   - Tracking handler: call service after entry

4. Unit tests
   - `tests/unit/test_gamification_service.py`
   - Test XP calculations, streak updates, achievement checks
   - Mock database

5. Update existing gamification tests
   - Ensure they work with new service layer

**Acceptance Criteria**:
- ✅ GamificationService implemented
- ✅ All gamification logic centralized in service
- ✅ Handlers use service (no direct gamification logic)
- ✅ Unit tests at 90%+ coverage
- ✅ Existing gamification features work unchanged

### Phase 4: HealthService (4 hours)

**Goal**: Implement HealthService for tracking and reminders

**Tasks**:
1. Implement `HealthService`
   - Tracking category management
   - Tracking entry logging and retrieval
   - Reminder creation and management
   - Trend calculation
   - Health report generation

2. Refactor tracking handlers
   - Extract logic from agent tools
   - Use `HealthService` for tracking operations

3. Refactor reminder handlers
   - Update `handlers/reminders.py` to use service
   - Keep Telegram button logic in handler
   - Move business logic to service

4. Integrate reminder manager
   - Pass reminder_manager to HealthService via container
   - Service coordinates database + scheduler

5. Unit tests
   - `tests/unit/test_health_service.py`
   - Test tracking, reminders, trends, reports
   - Mock database and reminder_manager

6. Integration tests
   - `tests/integration/test_health_service_flow.py`
   - End-to-end tracking and reminder flows

**Acceptance Criteria**:
- ✅ HealthService implemented
- ✅ Tracking handlers refactored
- ✅ Reminder handlers refactored
- ✅ Unit tests at 90%+ coverage
- ✅ Integration tests pass
- ✅ No database calls in tracking/reminder handlers

### Phase 5: Handler Cleanup & Testing (3 hours)

**Goal**: Final cleanup, ensure no database calls in handlers, comprehensive testing

**Tasks**:
1. Audit all handlers for direct database calls
   - Use grep to find `from src.db.queries import`
   - Refactor any remaining direct calls

2. Refactor `src/agent/__init__.py`
   - Agent tools should use services
   - Pass service container to agent context

3. Update API routes to use services
   - `src/api/routes.py` should use services
   - No direct database calls in API

4. Documentation
   - Update README with architecture diagram
   - Document service interfaces
   - Add examples of using services

5. Comprehensive testing
   - Run full test suite
   - Fix any broken tests
   - Ensure 90%+ service test coverage

6. Performance testing
   - Verify no performance regression
   - Service layer should be lightweight

**Acceptance Criteria**:
- ✅ Zero direct database calls in handlers (grep verification)
- ✅ Zero direct database calls in API routes
- ✅ Agent uses services
- ✅ All tests pass (unit + integration)
- ✅ Service test coverage 90%+
- ✅ Documentation updated
- ✅ No performance regression

## Testing Strategy

### Unit Tests (Per Service)

**Structure**:
```
tests/unit/
├── test_user_service.py
├── test_food_service.py
├── test_gamification_service.py
└── test_health_service.py
```

**Approach**:
- Mock database connection
- Mock external dependencies (vision AI, memory manager, reminder manager)
- Test business logic in isolation
- Test error handling and edge cases
- Target: 90%+ coverage per service

**Example**:
```python
# tests/unit/test_user_service.py

import pytest
from unittest.mock import AsyncMock, MagicMock
from src.services.user_service import UserService

@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.connection = AsyncMock()
    return db

@pytest.fixture
def user_service(mock_db):
    return UserService(mock_db)

@pytest.mark.asyncio
async def test_create_user_success(user_service, mock_db):
    # Setup
    telegram_id = "12345"
    mock_cursor = AsyncMock()
    mock_db.connection.return_value.__aenter__.return_value = AsyncMock()

    # Execute
    result = await user_service.create_user(telegram_id)

    # Assert
    assert result["success"] is True
    assert result["telegram_id"] == telegram_id
    mock_cursor.execute.assert_called_once()
```

### Integration Tests

**Focus**: Test service + database interactions with real database (test DB)

**Structure**:
```
tests/integration/
├── test_user_service_flow.py
├── test_food_service_flow.py
├── test_gamification_service_flow.py
└── test_health_service_flow.py
```

**Approach**:
- Use test database (PostgreSQL in Docker)
- Test complete flows end-to-end
- Verify database state changes
- Test service-to-service interactions

### Handler Tests

**Update existing handler tests to mock services**:
```python
# tests/unit/test_handlers.py (updated)

from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
@patch('src.handlers.onboarding.get_container')
async def test_onboarding_start(mock_get_container, update, context):
    # Mock container and service
    mock_container = MagicMock()
    mock_user_service = AsyncMock()
    mock_container.user_service = mock_user_service
    mock_get_container.return_value = mock_container

    # Execute handler
    await handle_onboarding_start(update, context)

    # Assert service was called
    mock_user_service.get_user.assert_called_once()
```

## Migration Path & Backwards Compatibility

### Safe Migration
1. **Keep `db/queries.py` intact** during migration
2. Services initially call existing query functions
3. Handlers gradually migrated one at a time
4. Tests verify behavior unchanged
5. After all handlers use services, refactor queries into repositories if needed

### Rollback Plan
- Each phase is independently deployable
- If Phase N fails, previous phases still work
- Feature flags for gradual rollout (if needed)

## Success Metrics

### Code Quality
- ✅ Handler files reduced by 50%+ lines of code
- ✅ Business logic extracted to testable services
- ✅ Service test coverage 90%+
- ✅ No `from src.db.queries import` in handlers (except repositories)

### Maintainability
- ✅ New features can be added to services without touching handlers
- ✅ Services can be reused from API, CLI, or other interfaces
- ✅ Clear separation of concerns (Telegram logic vs business logic)

### Testing
- ✅ Handler tests simplified (mock services, not database)
- ✅ Service logic testable without Telegram context
- ✅ Faster unit tests (no database for service tests)

## Definition of Done

- ✅ All 4 services implemented (User, Food, Gamification, Health)
- ✅ Dependency injection working with ServiceContainer
- ✅ All handlers refactored to use services
- ✅ Zero direct database calls in handlers (grep verified)
- ✅ Agent tools use services
- ✅ API routes use services
- ✅ Service tests at 90%+ coverage
- ✅ All existing tests pass (no regressions)
- ✅ Handler tests use service mocks
- ✅ Documentation updated with architecture diagram

## Risks & Mitigation

### Risk 1: Breaking Existing Functionality
**Mitigation**:
- Comprehensive test coverage before refactoring
- Incremental migration (one handler at a time)
- Keep database queries intact initially

### Risk 2: Performance Regression
**Mitigation**:
- Service layer should be thin wrappers
- No unnecessary abstraction overhead
- Performance tests before/after

### Risk 3: Over-Engineering
**Mitigation**:
- Simple DI container (no framework)
- Services are just organized business logic
- Don't add patterns not needed yet

### Risk 4: Testing Complexity
**Mitigation**:
- Clear mock patterns established early
- Reusable test fixtures
- Integration tests for critical flows

## Future Enhancements (Out of Scope)

**Not included in this phase**:
- Repository pattern (queries.py already serves this role)
- Domain events / event-driven architecture
- CQRS (Command Query Responsibility Segregation)
- Service-to-service async messaging
- Microservices split

**Potential Phase 4 work**:
- GraphQL API using services
- CLI interface using services
- Background job system using services
- Webhook interface using services

## References

- **Epic**: [epic-008-phase3-architecture.md](https://github.com/gpt153/health-agent-planning/blob/main/.bmad/epic-008-phase3-architecture.md)
- **Related Issues**: Phase 2 completion (prerequisite)
- **Architecture Patterns**: Layered Architecture, Service Layer Pattern, Dependency Injection

---

**Plan Created**: 2026-01-15
**Last Updated**: 2026-01-15
**Status**: Ready for Implementation
**Estimated Duration**: 16-20 hours across 5 phases
