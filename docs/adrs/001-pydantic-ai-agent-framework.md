# ADR-001: PydanticAI for Conversational AI Framework

**Status**: Accepted

**Date**: 2024-01-15

**Deciders**: Health Agent Development Team

---

## Context

The Health Agent project requires a robust conversational AI framework to power its health coaching capabilities through Telegram. The system needs to:

- Support tool calling for actions like saving food entries, managing reminders, and gamification
- Provide type-safe interfaces between the AI and application logic
- Handle structured outputs with validation
- Support multiple LLM providers (OpenAI GPT-4o, Anthropic Claude 3.5 Sonnet)
- Integrate seamlessly with Python async/await patterns
- Enable testability and maintainability

## Decision

We have chosen **PydanticAI** as our conversational AI framework over alternatives like LangChain, AutoGPT, or building a custom solution.

## Rationale

### Why PydanticAI?

1. **Type Safety with Pydantic**
   - Full typing support with Pydantic v2 validation
   - Structured outputs are validated at runtime
   - Tool parameters are type-checked automatically
   - Reduces runtime errors and improves IDE support

2. **Clean Tool Interface**
   - Tools are defined as standard Python async functions
   - Decorated with `@agent.tool()` for registration
   - RunContext pattern provides dependency injection
   - Clear separation between tool logic and AI orchestration

3. **Multi-Model Support**
   - Provider-agnostic abstraction layer
   - Easy switching between OpenAI, Anthropic, Gemini, etc.
   - Model-specific features (Claude's thinking, GPT-4o vision) accessible
   - Cost optimization through model selection

4. **Integration with Python Ecosystem**
   - Built on FastAPI/Pydantic patterns familiar to team
   - Native async/await support
   - Works seamlessly with SQLAlchemy, PostgreSQL, etc.
   - Minimal dependencies compared to LangChain

5. **Structured Conversation Management**
   - Clear message history management
   - System prompt configuration
   - Dynamic tool registration
   - Stateful conversation handling through RunContext

### Alternatives Considered

#### LangChain
**Rejected because**:
- Heavy framework with steep learning curve
- Complex abstractions (Chains, Agents, Tools, Memory) that add cognitive overhead
- Less type-safe (dynamic tool loading, loose typing)
- Larger dependency tree increases maintenance burden
- Over-engineered for our use case (we need conversational AI, not a general-purpose LLM framework)

**Pros we considered**:
- Larger ecosystem and community
- More pre-built integrations
- Extensive documentation

#### AutoGPT / Agent frameworks
**Rejected because**:
- Designed for autonomous agents, not conversational assistants
- Loop-based execution model doesn't fit health coaching workflow
- Less control over agent behavior
- Overkill for our scoped health tracking use case

#### Custom Solution
**Rejected because**:
- Reinventing tool calling and structured outputs is complex
- Maintaining compatibility with multiple LLM APIs requires ongoing effort
- Type safety would require significant custom validation code
- Team velocity would decrease

## Implementation Details

### Agent Architecture

```python
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIModel

# Define typed dependencies
class AgentDeps(TypedDict):
    user_id: str
    db_manager: DatabaseManager
    memory_manager: MemoryFileManager
    # ... other services

# Create agents with different models
claude_agent = Agent(
    model="claude-3-5-sonnet-20241022",
    system_prompt=SYSTEM_PROMPT,
    deps_type=AgentDeps,
    retries=2
)

gpt_agent = Agent(
    model="openai:gpt-4o",
    system_prompt=SYSTEM_PROMPT,
    deps_type=AgentDeps,
    retries=2
)

# Define tools with type safety
@claude_agent.tool()
@gpt_agent.tool()
async def save_food_entry(
    ctx: RunContext[AgentDeps],
    foods: list[dict],
    calories: int,
    protein: float,
    carbs: float,
    fat: float
) -> str:
    """Save a food entry to the database."""
    await ctx.deps["db_manager"].save_food_entry(
        user_id=ctx.deps["user_id"],
        foods=foods,
        calories=calories,
        # ...
    )
    return "Food entry saved successfully"
```

### Tool Registration Pattern

- Tools are registered on both agents (Claude and GPT-4o) for dual-model support
- Each tool is an async function with typed parameters
- RunContext provides dependency injection for database, memory, services
- Return values are strings (agent-friendly responses)

### Conversation Flow

1. User message received via Telegram
2. Message added to conversation history
3. Agent.run_sync() called with message and dependencies
4. Agent decides which tools to call (if any)
5. Tools execute with access to services via RunContext
6. Agent generates response based on tool outputs
7. Response sent back to user

## Consequences

### Positive

✅ **Type Safety**: Pydantic validation catches errors at development time
✅ **Maintainability**: Clean, readable code with minimal boilerplate
✅ **Testability**: Tools are pure functions, easy to unit test
✅ **Flexibility**: Easy to swap LLM providers or add new tools
✅ **Developer Experience**: Great IDE support with type hints
✅ **Performance**: Async-first design scales well
✅ **Integration**: Works seamlessly with FastAPI, SQLAlchemy, PostgreSQL

### Negative

⚠️ **Framework Maturity**: PydanticAI is newer (released 2024) compared to LangChain
⚠️ **Community Size**: Smaller community means fewer Stack Overflow answers
⚠️ **Pre-built Integrations**: Fewer out-of-the-box integrations than LangChain
⚠️ **Learning Curve**: Team needs to learn PydanticAI-specific patterns

### Risks and Mitigations

| Risk | Mitigation |
|------|-----------|
| Framework abandoned by maintainers | PydanticAI is maintained by Pydantic team (trusted organization) |
| Breaking changes in updates | Pin dependency versions, test before upgrading |
| Missing features compared to LangChain | Implement custom solutions (we've already built multi-agent consensus, memory systems) |
| Limited documentation | Contribute back to community, maintain internal docs |

## Code Examples

### Multi-Agent Nutrition Consensus

Our custom implementation using PydanticAI shows its flexibility:

```python
async def multi_agent_nutrition_consensus(photo_path: str) -> dict:
    """Use 3 specialist agents + 1 moderator for accurate calorie estimation."""

    # Three specialist agents with different biases
    conservative_estimate = await conservative_agent.run_sync(photo_path)
    moderate_estimate = await moderate_agent.run_sync(photo_path)
    optimistic_estimate = await optimistic_agent.run_sync(photo_path)

    # Moderator agent builds consensus
    consensus = await moderator_agent.run_sync(
        f"Conservative: {conservative_estimate}\n"
        f"Moderate: {moderate_estimate}\n"
        f"Optimistic: {optimistic_estimate}"
    )

    return consensus.data  # Structured output with Pydantic validation
```

### Dynamic Tool Creation

Users can create custom tracking tools at runtime:

```python
def create_dynamic_tool(tool_name: str, description: str):
    """Create a new tool dynamically based on user preferences."""

    @claude_agent.tool()
    @gpt_agent.tool()
    async def dynamic_tool(ctx: RunContext[AgentDeps], value: str) -> str:
        # Tool logic here
        await ctx.deps["db_manager"].save_custom_metric(
            user_id=ctx.deps["user_id"],
            metric_name=tool_name,
            value=value
        )
        return f"{tool_name} saved: {value}"

    # Tool is now available to agents
    return dynamic_tool
```

## Related Decisions

- **ADR-002**: Three-tier memory architecture leverages PydanticAI's RunContext for dependency injection
- **ADR-004**: Multi-agent nutrition consensus built on PydanticAI's agent primitives
- **ADR-003**: Service layer architecture integrates cleanly with PydanticAI's tool system

## References

- [PydanticAI Documentation](https://ai.pydantic.dev/)
- [PydanticAI GitHub Repository](https://github.com/pydantic/pydantic-ai)
- [Pydantic v2 Documentation](https://docs.pydantic.dev/)
- Health Agent Implementation: `/src/agent/__init__.py`

## Revision History

- 2024-01-15: Initial decision (PydanticAI selected)
- 2024-12-20: Multi-agent consensus system implemented
- 2025-01-18: Documentation created for Phase 3.7
