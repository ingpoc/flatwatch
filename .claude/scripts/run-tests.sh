#!/bin/bash
# run-tests.sh - Run FlatWatch tests
#
# Runs frontend (Jest) and backend (pytest) tests
#
# Usage: ./run-tests.sh [--frontend|--backend|--coverage]

set -e

RUN_FRONTEND=true
RUN_BACKEND=true
COVERAGE=""

while [[ $# -gt 0 ]]; do
  case $1 in
    --no-frontend)
      RUN_FRONTEND=false
      shift
      ;;
    --no-backend)
      RUN_BACKEND=false
      shift
      ;;
    --coverage)
      COVERAGE="--coverage"
      shift
      ;;
    *)
      echo "Usage: $0 [--no-frontend] [--no-backend] [--coverage]"
      exit 1
      ;;
  esac
done

echo "=== FlatWatch Test Suite ==="

PASS=0
FAIL=0

# ============================================================================
# Backend tests (pytest)
# ============================================================================

if [ "$RUN_BACKEND" = true ]; then
  if [ -d "backend" ]; then
    echo ""
    echo "Running backend tests..."

    cd backend

    if [ -f "venv/bin/activate" ]; then
      source venv/bin/activate
    fi

    if pytest tests/ -v $COVERAGE 2>/dev/null; then
      echo "✓ Backend tests passed"
      PASS=$((PASS + 1))
    else
      echo "✗ Backend tests failed" >&2
      FAIL=$((FAIL + 1))
    fi

    cd ..
  else
    echo "⚠ backend/ not found, skipping backend tests" >&2
  fi
fi

# ============================================================================
# Frontend tests (Jest/Vitest)
# ============================================================================

if [ "$RUN_FRONTEND" = true ]; then
  if [ -d "frontend" ]; then
    echo ""
    echo "Running frontend tests..."

    cd frontend

    if npm test -- --run $COVERAGE 2>/dev/null; then
      echo "✓ Frontend tests passed"
      PASS=$((PASS + 1))
    else
      echo "✗ Frontend tests failed" >&2
      FAIL=$((FAIL + 1))
    fi

    cd ..
  else
    echo "⚠ frontend/ not found, skipping frontend tests" >&2
  fi
fi

# ============================================================================
# Summary
# ============================================================================

echo ""
echo "=== Test Summary ==="
echo "Passed: $PASS | Failed: $FAIL"

if [ $FAIL -eq 0 ]; then
  echo "✅ All tests passed"
  exit 0
else
  echo "❌ Some tests failed"
  exit 1
fi
