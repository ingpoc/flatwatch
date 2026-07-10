# FlatWatch QA

Pointer only. **Do not** keep a ledger or grader copy here.

Portfolio control owner: [`../aadhaar-chain/qa/docs/workflow/README.md`](../../aadhaar-chain/qa/docs/workflow/README.md)

Run from `aadhaar-chain/qa`:

```bash
cd ../aadhaar-chain/qa
npm run grade:deterministic && npm run grade:browser && npm run grade:wallet
```

Repo-local notes (not portfolio ownership):
- Server-side AadhaarChain trust on receipt upload, OCR, challenge create/resolve
- Receipt list date parsing accepts ISO `created_at`
