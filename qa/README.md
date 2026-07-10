# FlatWatch QA notes

See portfolio ledger in `test-ledger.json` (and full harness under `aadhaar-chain/qa`).

Root-cause fixes validated here:
- Server-side AadhaarChain trust enforcement on receipt upload, OCR process, challenge create/resolve
- Receipt list date parsing accepts ISO `created_at` (was treating ISO as unix seconds → `Invalid time value`)
