# AGENTS.md

## Instruction Inheritance

- Read `../AGENTS.md` first for portfolio-wide governance.
- This file adds only `flatwatch`-specific execution guidance.
- If this file conflicts with the root workspace `AGENTS.md`, the root file wins unless it explicitly allows a repo-local exception.
- `CLAUDE.md` is optional context and not a separate policy authority.

## Repository Type

- FlatWatch is a full-stack application with a Python backend and a Next.js frontend.

## Repo-Specific Verification

- Backend changes should be validated from `backend`.
- Frontend changes should be validated from `frontend`.
- BEFORE portfolio browser / same-wallet testing -> read `../aadhaar-chain/qa/docs/workflow/browser-testing-control-plane.md` then `../aadhaar-chain/qa/docs/workflow/portfolio-browser-acceptance-loop.md`.
- Session friction / standing traps -> `../aadhaar-chain/qa/docs/workflow/session-friction-log.md`.
- FlatWatch is a trust consumer: confirm AadhaarChain verified trust before concluding elevated receipt/challenge/agent failures.
- Local ledger mirror: `qa/test-ledger.json`. Prefer running graders from `aadhaar-chain/qa`.
