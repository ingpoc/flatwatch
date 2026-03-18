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

## Browser Testing

- BEFORE browser testing FlatWatch -> read `../docs/workflow/browser-testing-control-plane.md`
- BEFORE validating the same-user portfolio journey -> read `../docs/workflow/portfolio-browser-acceptance-loop.md`
- Browser testing for this repo should happen after AadhaarChain trust state is confirmed, because transparency actions are expected to read shared trust state.
- Critical browser routes for this repo: `/`, `/dashboard`, `/receipts`, `/challenges`, `/chat`
- Browser conclusions are valid only when both the frontend and backend are running and the trust panel can resolve the AadhaarChain state.
