#!/bin/bash
#
# Load Test Runner Script
#
# Executes all load test scenarios in sequence with monitoring
# and generates consolidated performance report.
#
# Usage:
#   ./load_tests/run_load_tests.sh [scenario]
#
# Arguments:
#   scenario - Optional. Run specific scenario: steady, spike, endurance, or all (default)
#
# Examples:
#   ./load_tests/run_load_tests.sh           # Run all scenarios
#   ./load_tests/run_load_tests.sh steady    # Run only steady load test
#
# Environment Variables:
#   LOAD_TEST_HOST - Target host (default: http://localhost:8000)
#   SKIP_HEALTH_CHECK - Skip health check (default: false)
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
RESULTS_DIR="$SCRIPT_DIR/results"
LOAD_TEST_HOST="${LOAD_TEST_HOST:-http://localhost:8000}"
SCENARIO="${1:-all}"

# Create results directory
mkdir -p "$RESULTS_DIR"

# Print header
echo ""
echo "=========================================="
echo "🚀 HEALTH AGENT LOAD TEST SUITE"
echo "=========================================="
echo "Host: $LOAD_TEST_HOST"
echo "Scenario: $SCENARIO"
echo "Results: $RESULTS_DIR"
echo "=========================================="
echo ""

# Health check function
health_check() {
    echo -e "${BLUE}🏥 Performing health check...${NC}"

    if [ "${SKIP_HEALTH_CHECK}" = "true" ]; then
        echo -e "${YELLOW}⚠️  Health check skipped (SKIP_HEALTH_CHECK=true)${NC}"
        return 0
    fi

    # Check if API is reachable
    if curl -s -f "$LOAD_TEST_HOST/health" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ API is healthy${NC}"
        return 0
    else
        echo -e "${RED}❌ API health check failed${NC}"
        echo -e "${YELLOW}   Make sure the API is running: docker-compose up -d${NC}"
        exit 1
    fi
}

# Run scenario function
run_scenario() {
    local scenario_name=$1
    local scenario_file="$SCRIPT_DIR/scenarios/${scenario_name}.py"

    if [ ! -f "$scenario_file" ]; then
        echo -e "${RED}❌ Scenario not found: $scenario_file${NC}"
        return 1
    fi

    echo ""
    echo "=========================================="
    echo -e "${BLUE}📊 Running: ${scenario_name}${NC}"
    echo "=========================================="

    # Extract scenario configuration
    USERS=$(python3 -c "import sys; sys.path.insert(0, '$SCRIPT_DIR'); from scenarios.$scenario_name import USERS; print(USERS)")
    SPAWN_RATE=$(python3 -c "import sys; sys.path.insert(0, '$SCRIPT_DIR'); from scenarios.$scenario_name import SPAWN_RATE; print(SPAWN_RATE)")
    RUN_TIME=$(python3 -c "import sys; sys.path.insert(0, '$SCRIPT_DIR'); from scenarios.$scenario_name import RUN_TIME; print(RUN_TIME)")
    DESCRIPTION=$(python3 -c "import sys; sys.path.insert(0, '$SCRIPT_DIR'); from scenarios.$scenario_name import DESCRIPTION; print(DESCRIPTION)")

    echo "Config: $DESCRIPTION"
    echo "Users: $USERS, Spawn rate: $SPAWN_RATE/s, Duration: $RUN_TIME"
    echo ""

    # Start time
    start_time=$(date +%s)

    # Run Locust test
    cd "$PROJECT_ROOT"
    locust \
        -f "$SCRIPT_DIR/locustfile.py" \
        --host "$LOAD_TEST_HOST" \
        --users "$USERS" \
        --spawn-rate "$SPAWN_RATE" \
        --run-time "$RUN_TIME" \
        --headless \
        --only-summary \
        --html "$RESULTS_DIR/${scenario_name}_report.html" \
        --csv "$RESULTS_DIR/${scenario_name}" \
        2>&1 | tee "$RESULTS_DIR/${scenario_name}.log"

    # End time
    end_time=$(date +%s)
    duration=$((end_time - start_time))

    echo ""
    echo -e "${GREEN}✅ Completed in ${duration}s${NC}"
    echo -e "${BLUE}📄 Report: $RESULTS_DIR/${scenario_name}_report.html${NC}"
    echo ""
}

# Check success criteria
check_success_criteria() {
    local scenario_name=$1
    local csv_file="$RESULTS_DIR/${scenario_name}_stats.csv"

    if [ ! -f "$csv_file" ]; then
        echo -e "${YELLOW}⚠️  No stats file found: $csv_file${NC}"
        return 0
    fi

    echo -e "${BLUE}🎯 Checking success criteria for $scenario_name...${NC}"

    # Extract P95 and failure rate from CSV (second row, aggregate stats)
    # CSV format: Type,Name,Request Count,Failure Count,Median,Average,Min,Max,Content Size,Requests/s,Failures/s,50%,66%,75%,80%,90%,95%,98%,99%,99.9%,99.99%,100%

    # Get P95 from column 17 (95th percentile)
    p95=$(awk -F',' 'NR==2 {print $17}' "$csv_file")

    # Get failure rate (failures / total requests * 100)
    total_requests=$(awk -F',' 'NR==2 {print $3}' "$csv_file")
    failures=$(awk -F',' 'NR==2 {print $4}' "$csv_file")

    if [ -z "$p95" ] || [ -z "$total_requests" ] || [ -z "$failures" ]; then
        echo -e "${YELLOW}⚠️  Could not extract metrics from CSV${NC}"
        return 0
    fi

    # Calculate failure rate
    if [ "$total_requests" -gt 0 ]; then
        failure_rate=$(awk "BEGIN {printf \"%.2f\", ($failures / $total_requests) * 100}")
    else
        failure_rate=0
    fi

    # Get thresholds from scenario config
    MAX_P95_MS=$(python3 -c "import sys; sys.path.insert(0, '$SCRIPT_DIR'); from scenarios.$scenario_name import MAX_P95_MS; print(MAX_P95_MS)")
    MAX_FAILURE_RATE=$(python3 -c "import sys; sys.path.insert(0, '$SCRIPT_DIR'); from scenarios.$scenario_name import MAX_FAILURE_RATE; print(MAX_FAILURE_RATE)")

    # Convert P95 to seconds
    p95_s=$(awk "BEGIN {printf \"%.2f\", $p95 / 1000}")
    max_p95_s=$(awk "BEGIN {printf \"%.2f\", $MAX_P95_MS / 1000}")

    echo "  P95 Latency: ${p95_s}s (threshold: ${max_p95_s}s)"
    echo "  Failure Rate: ${failure_rate}% (threshold: ${MAX_FAILURE_RATE}%)"

    # Check P95
    p95_pass=$(awk "BEGIN {print ($p95 < $MAX_P95_MS) ? 1 : 0}")
    if [ "$p95_pass" -eq 1 ]; then
        echo -e "  ${GREEN}✅ P95 < ${max_p95_s}s: PASS${NC}"
    else
        echo -e "  ${RED}❌ P95 < ${max_p95_s}s: FAIL${NC}"
    fi

    # Check failure rate
    failure_pass=$(awk "BEGIN {print ($failure_rate < $MAX_FAILURE_RATE) ? 1 : 0}")
    if [ "$failure_pass" -eq 1 ]; then
        echo -e "  ${GREEN}✅ Errors < ${MAX_FAILURE_RATE}%: PASS${NC}"
    else
        echo -e "  ${RED}❌ Errors < ${MAX_FAILURE_RATE}%: FAIL${NC}"
    fi

    echo ""
}

# Main execution
main() {
    # Health check
    health_check

    # Run scenarios
    case "$SCENARIO" in
        steady)
            run_scenario "steady_load"
            check_success_criteria "steady_load"
            ;;
        spike)
            run_scenario "spike_test"
            check_success_criteria "spike_test"
            ;;
        endurance)
            run_scenario "endurance_test"
            check_success_criteria "endurance_test"
            ;;
        all)
            run_scenario "steady_load"
            check_success_criteria "steady_load"

            run_scenario "spike_test"
            check_success_criteria "spike_test"

            run_scenario "endurance_test"
            check_success_criteria "endurance_test"
            ;;
        *)
            echo -e "${RED}❌ Invalid scenario: $SCENARIO${NC}"
            echo "Valid scenarios: steady, spike, endurance, all"
            exit 1
            ;;
    esac

    # Summary
    echo ""
    echo "=========================================="
    echo -e "${GREEN}✅ LOAD TEST SUITE COMPLETE${NC}"
    echo "=========================================="
    echo -e "Results available in: ${BLUE}$RESULTS_DIR${NC}"
    echo ""
    echo "HTML Reports:"
    for report in "$RESULTS_DIR"/*_report.html; do
        if [ -f "$report" ]; then
            echo "  - $(basename "$report")"
        fi
    done
    echo ""
}

# Run main function
main
