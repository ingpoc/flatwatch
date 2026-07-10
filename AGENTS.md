# AGENTS.md

## Scope

Repo-local guidance for `flatwatch` only.

**Portfolio QA / browser / same-wallet control owner:** `../aadhaar-chain/qa/docs/workflow/`  
Entry: `../aadhaar-chain/qa/docs/workflow/README.md`

There is no parent `../AGENTS.md` in this multi-repo checkout. Do not invent one. Do not fork the ledger or graders under this repo.

`CLAUDE.md` is optional context, not a separate policy authority.

## Repository Type

Full-stack: Python backend + Next.js frontend.

## Repo-Specific Verification

- Backend changes → validate from `backend`
- Frontend changes → validate from `frontend`
- Local ports: API `43104`, UI `43105`
- FlatWatch is a trust consumer: confirm AadhaarChain verified trust before concluding elevated receipt/challenge/agent failures
- BEFORE portfolio browser / same-wallet testing → control plane, then acceptance loop
- Session friction → `../aadhaar-chain/qa/docs/workflow/session-friction-log.md`
- Run graders only from `aadhaar-chain/qa` (no local ledger copy)
