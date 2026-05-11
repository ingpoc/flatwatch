# FlatWatch

`flatwatch` is the portfolio transparency and audit application for housing society finance workflows. It consumes AadhaarChain trust for elevated evidence, challenge, and agent workflows while keeping its app-local resident/admin auth separate.

It is currently a hardened POC/pilot candidate, not a fully production-wired society finance system.

## Local Services

| Service | URL |
| --- | --- |
| Frontend | `http://127.0.0.1:43105` |
| Backend | `http://127.0.0.1:43104` |
| AadhaarChain gateway | `http://127.0.0.1:43101` |

## Features

- Dashboard with financial summary and transaction list.
- Receipt upload and review workflow.
- Challenge creation and resolution workflow.
- Admin audit review surface.
- Chat Guard agent surface for trust-aware receipt, transaction, and dispute analysis.
- AadhaarChain trust consumption for elevated workflows.

## Architecture

| Layer | Technology |
| --- | --- |
| Frontend | Next.js 16, React 19, Tailwind CSS 4 |
| Backend | FastAPI, Python 3.12 |
| Local database | SQLite with idempotent migrations |
| Production database target | PostgreSQL |
| Auth | app-local resident/admin auth |
| Agent runtime | Claude Agent SDK path through backend control-plane routes |
| Trust producer | AadhaarChain gateway |

## Development

Backend:

```bash
cd backend
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /Users/gurusharan/.pyenv/versions/3.12.0/bin/python3 -m pytest -q -p pytest_asyncio.plugin --asyncio-mode=auto
python3 -m uvicorn app.main:app --host 127.0.0.1 --port 43104
```

Frontend:

```bash
cd frontend
npm install
npm test -- --runInBand
npm run lint
npm run build
npm run dev
```

The workspace deterministic gate runs both backend and frontend checks:

```bash
scripts/portfolio/acceptance-gate.sh --deterministic-only
```

The latest gate passed, including FlatWatch backend `125` tests and frontend Jest, ESLint, and Next build checks.

## Runtime Modes

Set `FLATWATCH_ENV` to one of:

- `demo`
- `staging`
- `production`

Production startup refuses unsafe demo defaults unless explicitly allowed by the operator. Production requires non-default `SECRET_KEY` and `ENCRYPTION_KEY` values and blocks demo/mock auth, mock Razorpay ingestion, and mock OCR unless the corresponding explicit override is set.

## Trust And Agent Flow

FlatWatch reads AadhaarChain trust for elevated transparency, evidence, challenge, and agent workflows.

Agent surface:

- route: `/chat`
- not route: `/agent`

Chrome validation in the signed wallet profile renders `/chat` with:

- wallet `C5svcE...g92YFF`
- runtime `local_cli`
- verified write path enabled

Chrome text-entry submission for new FlatWatch prompts is currently blocked by the Chrome plugin textarea/clipboard path, but the page, runtime, wallet, and trust state render correctly.

## POC And Production Gaps

Do not claim production readiness until these are wired to real managed services:

- replace demo/local auth for pilot and production
- replace mock Razorpay/MyGate-style ingestion with signed provider webhook verification, reconciliation, retry, and source references
- replace mock OCR/fallback extraction with real extraction, confidence, matching, manual review, and durable audit trail
- move local receipt files to private object storage with signed downloads, retention, deletion, and access audit logs
- keep agent write actions auditable and reversible where possible

## Pages

| Route | Purpose |
| --- | --- |
| `/` | Landing page |
| `/dashboard` | Financial summary and transaction overview |
| `/transactions` | Transaction list |
| `/receipts` | Receipt upload and review |
| `/challenges` | Challenge workflow |
| `/chat` | Chat Guard agent surface |
| `/audit` | Admin audit review |
