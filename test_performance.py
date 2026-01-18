"""
Performance Testing Script for Telegram Bot Response Latency
Measures actual timings at each stage of message processing

Enhanced with comprehensive metrics:
- System resource usage (CPU, memory)
- Database connection pool statistics
- Network I/O metrics
- Per-handler breakdown
- P50, P95, P99 latency percentiles
"""
import asyncio
import logging
import time
from datetime import datetime
import sys
from typing import Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import bot components
from src.db.queries import get_conversation_history, save_conversation_message
from src.memory.file_manager import memory_manager
from src.memory.mem0_manager import mem0_manager
from src.memory.system_prompt import generate_system_prompt
from src.agent import get_agent_response
from src.db.connection import db

# Import profiling utilities
from src.utils.profiling import PerformanceTimer, SystemMetrics, PerformanceMonitor

# Try to import psutil for enhanced metrics
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logger.warning("psutil not available - system metrics will be limited")


async def test_message_performance(user_id: str, message: str, test_name: str, monitor: Optional[PerformanceMonitor] = None):
    """
    Test performance of a single message through the entire pipeline.

    Args:
        user_id: Test user ID
        message: Message to send
        test_name: Descriptive name for this test
        monitor: Optional performance monitor for tracking metrics
    """
    print(f"\n{'='*80}")
    print(f"🧪 TEST: {test_name}")
    print(f"👤 User: {user_id}")
    print(f"💬 Message: {message}")
    print(f"{'='*80}\n")

    timings = {}

    # Capture initial system state
    initial_metrics = SystemMetrics.get_snapshot()
    print(f"📊 Initial State:")
    print(f"   ↳ Memory: {initial_metrics['memory_mb']:.2f} MB")
    print(f"   ↳ CPU: {initial_metrics['cpu_percent']:.1f}%\n")

    # Stage 1: Load conversation history
    with PerformanceTimer("1. Load Conversation History") as timer:
        message_history = await get_conversation_history(user_id, limit=20)
    timings['conversation_history'] = timer.duration_ms
    print(f"   ↳ Loaded {len(message_history)} messages")

    # Stage 2: Load user memory (file I/O)
    with PerformanceTimer("2. Load User Memory (Files)") as timer:
        user_memory = await memory_manager.load_user_memory(user_id)
    timings['load_memory'] = timer.duration_ms
    print(f"   ↳ Loaded {len(user_memory)} memory sections")

    # Stage 3: Generate system prompt (includes Mem0 search)
    with PerformanceTimer("3. Generate System Prompt (+ Mem0 Search)") as timer:
        system_prompt = generate_system_prompt(user_memory, user_id=user_id, current_query=message)
    timings['system_prompt'] = timer.duration_ms
    print(f"   ↳ System prompt length: {len(system_prompt)} chars")

    # Stage 4: Get agent response (LLM API call + tool registration)
    with PerformanceTimer("4. Agent Response (LLM API + Tools)") as timer:
        response = await get_agent_response(
            user_id, message, memory_manager, None, message_history
        )
    timings['agent_response'] = timer.duration_ms
    print(f"   ↳ Response length: {len(response)} chars")

    # Stage 5: Save conversation messages
    with PerformanceTimer("5. Save Conversation Messages") as timer:
        await save_conversation_message(user_id, "user", message, message_type="text")
        await save_conversation_message(user_id, "assistant", response, message_type="text")
    timings['save_messages'] = timer.duration_ms

    # Stage 6: Mem0 add_message (embedding generation)
    with PerformanceTimer("6. Mem0 Add Message (Embedding)") as timer:
        mem0_manager.add_message(user_id, message, role="user", metadata={"message_type": "text"})
        mem0_manager.add_message(user_id, response, role="assistant", metadata={"message_type": "text"})
    timings['mem0_add'] = timer.duration_ms

    # Calculate total time
    total_time = sum(timings.values())
    timings['total'] = total_time

    # Capture final system state
    final_metrics = SystemMetrics.get_snapshot()
    memory_delta = final_metrics['memory_mb'] - initial_metrics['memory_mb']

    # Print summary
    print(f"\n📊 TIMING BREAKDOWN:")
    print(f"{'─'*80}")
    for stage, duration in timings.items():
        if stage != 'total':
            percentage = (duration / total_time) * 100
            print(f"  {stage:40s}: {duration:8.2f}ms ({duration/1000:6.2f}s) [{percentage:5.1f}%]")
    print(f"{'─'*80}")
    print(f"  {'TOTAL':40s}: {total_time:8.2f}ms ({total_time/1000:6.2f}s) [100.0%]")
    print(f"{'─'*80}")

    # System resource changes
    print(f"\n💾 RESOURCE USAGE:")
    print(f"{'─'*80}")
    print(f"  Memory: {initial_metrics['memory_mb']:.2f} MB → {final_metrics['memory_mb']:.2f} MB (Δ {memory_delta:+.2f} MB)")
    print(f"  CPU: {final_metrics['cpu_percent']:.1f}%")
    print(f"{'─'*80}\n")

    # Record in performance monitor if provided
    if monitor:
        monitor.record_sample(
            test_name=test_name,
            total_time_ms=total_time,
            memory_mb=final_metrics['memory_mb'],
            memory_delta_mb=memory_delta,
            **timings
        )

    return timings, response


async def profile_database_query(user_id: str):
    """
    Profile the conversation history database query
    """
    print(f"\n{'='*80}")
    print(f"🔍 DATABASE QUERY PROFILING")
    print(f"{'='*80}\n")

    async with db.connection() as conn:
        async with conn.cursor() as cur:
            # Test query with EXPLAIN ANALYZE
            with PerformanceTimer("EXPLAIN ANALYZE conversation_messages") as timer:
                await cur.execute("""
                    EXPLAIN ANALYZE
                    SELECT role, content, message_type, created_at, metadata
                    FROM conversation_messages
                    WHERE user_id = %s
                    ORDER BY created_at DESC
                    LIMIT 20
                """, (user_id,))
                results = await cur.fetchall()

            print("Query Plan:")
            for row in results:
                print(f"  {row[0]}")

            # Check for indexes
            print(f"\n🗂️  Checking indexes on conversation_messages table:")
            await cur.execute("""
                SELECT indexname, indexdef
                FROM pg_indexes
                WHERE tablename = 'conversation_messages'
            """)
            indexes = await cur.fetchall()

            if indexes:
                for idx_name, idx_def in indexes:
                    print(f"  ✓ {idx_name}")
                    print(f"    {idx_def}")
            else:
                print("  ⚠️  No indexes found!")

    return timer.duration_ms


async def check_database_pool_stats():
    """Check database connection pool statistics"""
    print(f"\n🔍 DATABASE CONNECTION POOL:")
    print(f"{'─'*80}")

    if hasattr(db, '_pool') and db._pool:
        pool = db._pool
        # Access pool stats if available
        try:
            # psycopg pool has these attributes
            pool_size = getattr(pool, 'size', 'N/A')
            pool_available = getattr(pool, 'available', 'N/A')

            print(f"  Pool Size: {pool_size}")
            print(f"  Available Connections: {pool_available}")
            print(f"  Active Connections: {pool_size - pool_available if isinstance(pool_size, int) and isinstance(pool_available, int) else 'N/A'}")
        except Exception as e:
            print(f"  ⚠️  Could not retrieve pool stats: {e}")
    else:
        print(f"  ⚠️  No connection pool initialized")

    print(f"{'─'*80}\n")


async def run_all_tests():
    """
    Run comprehensive performance tests with enhanced metrics
    """
    print("\n" + "="*80)
    print("🚀 TELEGRAM BOT PERFORMANCE ANALYSIS (ENHANCED)")
    print("="*80)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"CPU Cores: {SystemMetrics.get_cpu_count()}")
    print(f"Initial Memory: {SystemMetrics.get_memory_usage_mb():.2f} MB")
    print("="*80)

    # Initialize database connection pool
    print("\n🔌 Initializing database connection pool...")
    await db.init_pool()
    print("✓ Database pool initialized")

    # Check pool stats
    await check_database_pool_stats()

    # Test user (create if doesn't exist)
    test_user = "test_user_999888777"

    # Ensure user exists
    from src.db.queries import user_exists, create_user
    if not await user_exists(test_user):
        await create_user(test_user)
        await memory_manager.create_user_files(test_user)
        print(f"✓ Created test user: {test_user}\n")
    else:
        print(f"✓ Using existing test user: {test_user}\n")

    # Test cases with different complexities
    test_cases = [
        ("Simple greeting", "Hi"),
        ("Simple question", "How are you?"),
        ("Memory recall (if data exists)", "What did I eat yesterday?"),
        ("Tool-using query (if reminders exist)", "Show my reminders"),
        ("Complex query", "Can you analyze my nutrition progress this week and give me recommendations?"),
    ]

    all_results = []

    # Create performance monitor
    monitor = PerformanceMonitor("Baseline Tests")

    for test_name, message in test_cases:
        try:
            timings, response = await test_message_performance(test_user, message, test_name, monitor)
            all_results.append({
                'test': test_name,
                'message': message,
                'timings': timings,
                'response_preview': response[:100] if response else None
            })
        except Exception as e:
            logger.error(f"❌ Test '{test_name}' failed: {e}", exc_info=True)
            all_results.append({
                'test': test_name,
                'message': message,
                'error': str(e)
            })

    # Database profiling
    try:
        db_query_time = await profile_database_query(test_user)
    except Exception as e:
        logger.error(f"❌ Database profiling failed: {e}", exc_info=True)
        db_query_time = None

    # Generate summary report
    print("\n" + "="*80)
    print("📈 AGGREGATE RESULTS")
    print("="*80)

    if all_results:
        # Calculate averages
        avg_timings = {}
        successful_tests = [r for r in all_results if 'timings' in r]

        if successful_tests:
            for key in successful_tests[0]['timings'].keys():
                values = [r['timings'][key] for r in successful_tests]
                avg_timings[key] = sum(values) / len(values)

            print("\n⏱️  AVERAGE TIMINGS ACROSS ALL TESTS:")
            print("─"*80)
            total_avg = avg_timings.get('total', 0)
            for stage, avg_ms in avg_timings.items():
                if stage != 'total':
                    percentage = (avg_ms / total_avg) * 100 if total_avg > 0 else 0
                    print(f"  {stage:40s}: {avg_ms:8.2f}ms ({avg_ms/1000:6.2f}s) [{percentage:5.1f}%]")
            print("─"*80)
            print(f"  {'AVERAGE TOTAL':40s}: {total_avg:8.2f}ms ({total_avg/1000:6.2f}s)")
            print("─"*80)

            # Calculate percentiles using PerformanceMonitor
            print("\n📊 LATENCY PERCENTILES (total response time):")
            print("─"*80)
            summary = monitor.get_summary()
            if 'metrics' in summary and 'total' in summary['metrics']:
                total_metrics = summary['metrics']['total']
                print(f"  P50 (median): {total_metrics['p50']/1000:.2f}s")
                print(f"  P95:          {total_metrics['p95']/1000:.2f}s")
                print(f"  P99:          {total_metrics['p99']/1000:.2f}s")
                print(f"  Min:          {total_metrics['min']/1000:.2f}s")
                print(f"  Max:          {total_metrics['max']/1000:.2f}s")
            print("─"*80)

            # Identify bottlenecks
            print("\n🔴 TOP BOTTLENECKS (ranked by impact):")
            print("─"*80)

            bottleneck_stages = [(k, v) for k, v in avg_timings.items() if k != 'total']
            bottleneck_stages.sort(key=lambda x: x[1], reverse=True)

            for i, (stage, avg_ms) in enumerate(bottleneck_stages[:5], 1):
                percentage = (avg_ms / total_avg) * 100 if total_avg > 0 else 0
                impact = "🔴 CRITICAL" if percentage > 50 else "🟡 HIGH" if percentage > 20 else "🟢 MEDIUM"
                print(f"  {i}. {stage:35s}: {avg_ms/1000:6.2f}s ({percentage:5.1f}%) {impact}")
            print("─"*80)

    # Save detailed report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = f".agents/supervision/performance-findings-{timestamp}.md"

    with open(report_path, 'w') as f:
        f.write(f"# Performance Analysis Findings\n\n")
        f.write(f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**Test User**: {test_user}\n\n")
        f.write(f"---\n\n")

        f.write(f"## Executive Summary\n\n")
        if successful_tests:
            f.write(f"- **Tests Run**: {len(test_cases)}\n")
            f.write(f"- **Successful**: {len(successful_tests)}\n")
            f.write(f"- **Average Total Time**: {total_avg/1000:.2f}s\n")
            f.write(f"- **Slowest Component**: {bottleneck_stages[0][0]} ({bottleneck_stages[0][1]/1000:.2f}s)\n\n")

        f.write(f"---\n\n")
        f.write(f"## Detailed Results\n\n")

        for result in all_results:
            f.write(f"### Test: {result['test']}\n\n")
            f.write(f"**Message**: `{result['message']}`\n\n")

            if 'error' in result:
                f.write(f"❌ **Error**: {result['error']}\n\n")
            elif 'timings' in result:
                f.write(f"**Timing Breakdown**:\n\n")
                f.write(f"| Stage | Time (ms) | Time (s) | % of Total |\n")
                f.write(f"|-------|-----------|----------|------------|\n")

                total = result['timings']['total']
                for stage, duration in result['timings'].items():
                    if stage != 'total':
                        percentage = (duration / total) * 100 if total > 0 else 0
                        f.write(f"| {stage} | {duration:.2f} | {duration/1000:.2f} | {percentage:.1f}% |\n")

                f.write(f"| **TOTAL** | **{total:.2f}** | **{total/1000:.2f}** | **100.0%** |\n\n")

                if result.get('response_preview'):
                    f.write(f"**Response Preview**: {result['response_preview']}...\n\n")

            f.write(f"---\n\n")

        # Bottleneck analysis
        f.write(f"## Bottleneck Analysis\n\n")

        if successful_tests:
            f.write(f"### Average Timings\n\n")
            f.write(f"| Rank | Stage | Avg Time (s) | % of Total | Impact |\n")
            f.write(f"|------|-------|--------------|------------|--------|\n")

            for i, (stage, avg_ms) in enumerate(bottleneck_stages, 1):
                percentage = (avg_ms / total_avg) * 100 if total_avg > 0 else 0
                impact = "🔴 CRITICAL" if percentage > 50 else "🟡 HIGH" if percentage > 20 else "🟢 MEDIUM"
                f.write(f"| {i} | {stage} | {avg_ms/1000:.2f} | {percentage:.1f}% | {impact} |\n")

            f.write(f"\n")

        # Recommendations
        f.write(f"## Optimization Recommendations\n\n")

        if successful_tests and bottleneck_stages:
            top_bottleneck = bottleneck_stages[0]

            f.write(f"### Priority 1: {top_bottleneck[0]}\n\n")
            f.write(f"- **Current Time**: {top_bottleneck[1]/1000:.2f}s\n")

            if 'agent_response' in top_bottleneck[0].lower():
                f.write(f"- **Issue**: LLM API call latency\n")
                f.write(f"- **Quick Wins**:\n")
                f.write(f"  - Verify streaming is enabled\n")
                f.write(f"  - Add 'typing' indicator updates during long waits\n")
                f.write(f"  - Cache common responses\n")
                f.write(f"- **Long-term**:\n")
                f.write(f"  - Use faster model (Haiku) for simple queries\n")
                f.write(f"  - Implement response caching layer\n\n")

            elif 'mem0' in top_bottleneck[0].lower():
                f.write(f"- **Issue**: Semantic search latency\n")
                f.write(f"- **Quick Wins**:\n")
                f.write(f"  - Limit search to recent memories only\n")
                f.write(f"  - Disable for simple queries ('hi', 'thanks')\n")
                f.write(f"  - Cache search results per session\n")
                f.write(f"- **Long-term**:\n")
                f.write(f"  - Move to background/async task\n")
                f.write(f"  - Optimize pgvector indexes\n\n")

            elif 'system_prompt' in top_bottleneck[0].lower():
                f.write(f"- **Issue**: System prompt generation (includes Mem0)\n")
                f.write(f"- **Quick Wins**:\n")
                f.write(f"  - Cache prompt for session\n")
                f.write(f"  - Reduce Mem0 search limit\n")
                f.write(f"- **Long-term**:\n")
                f.write(f"  - Pre-generate prompts on background schedule\n\n")

            elif 'conversation_history' in top_bottleneck[0].lower():
                f.write(f"- **Issue**: Database query latency\n")
                f.write(f"- **Quick Wins**:\n")
                f.write(f"  - Add index on (user_id, created_at)\n")
                f.write(f"  - Reduce limit from 20 to 10 messages\n")
                f.write(f"- **Long-term**:\n")
                f.write(f"  - Implement Redis caching\n\n")

        f.write(f"---\n\n")
        f.write(f"## Database Query Analysis\n\n")

        if db_query_time:
            f.write(f"- **Query Execution Time**: {db_query_time:.2f}ms ({db_query_time/1000:.2f}s)\n")
            f.write(f"- See console output for EXPLAIN ANALYZE results\n\n")

        f.write(f"---\n\n")
        f.write(f"## Conclusion\n\n")

        if successful_tests:
            if total_avg > 60000:  # > 60 seconds
                f.write(f"🔴 **CRITICAL**: Average response time ({total_avg/1000:.2f}s) exceeds 60s target.\n\n")
            elif total_avg > 10000:  # > 10 seconds
                f.write(f"🟡 **WARNING**: Average response time ({total_avg/1000:.2f}s) exceeds 10s target.\n\n")
            else:
                f.write(f"🟢 **GOOD**: Average response time ({total_avg/1000:.2f}s) is acceptable.\n\n")

            f.write(f"**Target**: <10s total response time\n")
            f.write(f"**Current**: {total_avg/1000:.2f}s\n")
            f.write(f"**Gap**: {(total_avg/1000) - 10:.2f}s\n\n")

    print(f"\n✅ Report saved to: {report_path}")
    print(f"\n{'='*80}\n")

    # Close database pool
    print("🔌 Closing database connection pool...")
    await db.close_pool()
    print("✓ Database pool closed\n")


if __name__ == "__main__":
    try:
        asyncio.run(run_all_tests())
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
        sys.exit(1)
