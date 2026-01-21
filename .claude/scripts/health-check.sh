#!/bin/bash
# health-check.sh - Fast health diagnosis for FlatWatch
#
# Stack: Next.js (3000), FastAPI (8000), SQLite
#
# Exit codes:
#   0 = healthy
#   1 = broken (shows error immediately)
#   2 = timeout

set -e

FRONTEND_PORT=3000
BACKEND_PORT=8000
LOG_DIR="logs"
ISSUES_FOUND=0

echo "=== FlatWatch Health Check ==="

# ============================================================================
# Check infrastructure FIRST
# ============================================================================

check_infrastructure() {
  echo ""
  echo "Checking infrastructure..."

  # 1. SQLite database
  if [ -f "backend/data/flatwatch.db" ] || [ -f "data/flatwatch.db" ]; then
    echo "✓ SQLite database exists"
  else
    echo "⚠ SQLite database not found (will be created on first run)"
  fi

  # 2. Disk space
  local disk_usage=$(df -h . | tail -1 | awk '{print $5}' | sed 's/%//')
  if [ "$disk_usage" -gt 90 ]; then
    echo "✗ Disk space critically low: ${disk_usage}% used" >&2
    echo "Fix: Run 'docker system prune' or clean up node_modules" >&2
    ISSUES_FOUND=1
  elif [ "$disk_usage" -gt 80 ]; then
    echo "⚠ Disk space warning: ${disk_usage}% used" >&2
  else
    echo "✓ Disk space OK (${disk_usage}% used)"
  fi

  # 3. Required environment files
  echo ""
  echo "Checking environment files..."

  check_env_file() {
    local env_file=$1

    if [ ! -f "$env_file" ]; then
      echo "⚠ Missing: $env_file (may use defaults)" >&2
    else
      echo "✓ $(basename $env_file) exists"
    fi
  }

  check_env_file "backend/.env"
  check_env_file "frontend/.env.local"

  # Exit if infrastructure issues found
  if [ $ISSUES_FOUND -eq 1 ]; then
    echo "" >&2
    echo "❌ Infrastructure check FAILED" >&2
    exit 1
  fi
}

check_infrastructure

# ============================================================================
# Check service health
# ============================================================================

echo ""
echo "Checking services..."

check_service() {
  local url=$1
  local name=$2
  local log_file="$3"

  if curl -sf --max-time 2 "$url" > /dev/null 2>&1; then
    echo "✓ $name"
    return 0
  fi

  echo "✗ $name is NOT responding" >&2

  # Show process status
  local process_name=""
  if [ "$name" = "Backend" ]; then
    process_name="uvicorn"
  elif [ "$name" = "Frontend" ]; then
    process_name="next"
  fi

  if [ -n "$process_name" ]; then
    if pgrep -f "$process_name" >/dev/null 2>&1; then
      echo "  Process '$process_name' is running but not responding" >&2
    else
      echo "  Process '$process_name' is NOT running" >&2
    fi
  fi

  # Show log errors
  if [ -f "$log_file" ]; then
    echo "" >&2
    echo "Recent errors from $log_file:" >&2
    echo "---" >&2
    tail -50 "$log_file" | grep -iE "error|fatal|exception|failed|refused|denied" | tail -5 >&2 || echo "  (no recent errors)" >&2
    echo "---" >&2
  fi

  echo "" >&2
  echo "Fix: ./.claude/scripts/restart-servers.sh" >&2

  return 1
}

# Check frontend
if ! check_service "http://localhost:$FRONTEND_PORT" "Frontend" "$LOG_DIR/frontend.log"; then
  echo "" >&2
  echo "❌ Health check FAILED" >&2
  exit 1
fi

# Check backend (FastAPI health endpoint)
if ! check_service "http://localhost:$BACKEND_PORT/api/health" "Backend" "$LOG_DIR/backend.log"; then
  echo "" >&2
  echo "❌ Health check FAILED" >&2
  exit 1
fi

# ============================================================================
# Scan logs for warnings
# ============================================================================

echo ""
echo "Checking logs for warnings..."

WARNINGS=0

check_warnings() {
  local log_file=$1
  local service_name=$2

  if [ ! -f "$log_file" ]; then
    return 0
  fi

  local warnings=$(grep -iE "warning|deprecated|slow" "$log_file" 2>/dev/null | tail -3 || true)

  if [ -n "$warnings" ]; then
    echo "⚠ $service_name has warnings:" >&2
    echo "$warnings" >&2
    WARNINGS=1
  fi
}

check_warnings "$LOG_DIR/frontend.log" "Frontend"
check_warnings "$LOG_DIR/backend.log" "Backend"

# ============================================================================
# MCP servers
# ============================================================================

echo ""
echo "Checking MCP servers..."

MCP_RUNNING=0
if pgrep -f "token-efficient-mcp" >/dev/null 2>&1; then
  echo "✓ token-efficient-mcp running"
  MCP_RUNNING=1
fi

if pgrep -f "context-graph-mcp" >/dev/null 2>&1; then
  echo "✓ context-graph-mcp running"
  MCP_RUNNING=1
fi

if [ $MCP_RUNNING -eq 0 ]; then
  echo "⚠ No MCP servers detected" >&2
fi

# ============================================================================
# Final result
# ============================================================================

echo ""
if [ $WARNINGS -eq 0 ]; then
  echo "✅ All systems healthy"
  exit 0
else
  echo "⚠️  Services running but warnings found"
  exit 0
fi
