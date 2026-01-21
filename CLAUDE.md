---
name: project
description: society-transparency-system - unknown project
keywords: unknown, unknown, claude
project_type: unknown
framework: unknown
---

# society-transparency-system

**Purpose**: unknown project built with unknown.

---

## Project Overview

| Aspect | Details |
|--------|---------|
| **Type** | unknown |
| **Framework** | unknown |
| **Language** | Unknown |

---

## Architecture

### Tech Stack

| Layer | Technology |
|-------|------------|
| Language | Unknown |
| Framework | unknown |
| Package Manager |  echo "pip";; Node|JavaScript) echo "npm";; Rust) echo "cargo";; Go) echo "go modules";; *) echo "unknown";; esac) |

### Project Structure

| Directory | Purpose |
|-----------|---------|
| `.claude/` | Agent Harness configuration |
| `.claude/config/` | Project settings |
| `.claude/progress/` | State tracking |
| `.claude/scripts/` | Automation scripts (customizable) |

---

## Common Commands

| Task | Command |
|------|---------|
| Check state | `.claude/scripts/check-state.sh` |
| Get current feature | `.claude/scripts/get-current-feature.sh` |
| Health check | `.claude/scripts/health-check.sh` |
| Session entry | `~/.claude/skills/orchestrator/scripts/session-entry.sh` |

---

## Config Files

| File | Purpose |
|------|---------|
| `.claude/config/project.json` | Project settings (auto-detected) |
| `.claude/progress/state.json` | Current state |
| `.claude/progress/feature-list.json` | Features |
| `.claude/scripts/` | Project automation scripts (customizable) |

---

## MCP Servers

### token-efficient MCP

**Use for**: Data processing >50 items, CSV/logs, sandbox execution

| Tool | Use For | Savings |
|------|---------|---------|
| `execute_code` | Python/Bash/Node in sandbox | 98%+ |
| `process_csv` | CSV with filters | 99% |
| `process_logs` | Log pattern matching | 95% |

### context-graph MCP

**Use for**: Decision traces, semantic search, learning loops

| Tool | Purpose |
|------|---------|
| `context_store_trace` | Store decision with category + outcome |
| `context_query_traces` | Semantic search for similar decisions |
| `context_update_outcome` | Mark success/failure |
