# Testing Guide - FlatWatch Backend

## Test Coverage

**Total Tests: 92** ✅ All passing

### Test Files by Module

| Module | Tests | Coverage |
|--------|-------|----------|
| `test_auth.py` | 7 | Authentication endpoints |
| `test_rbac.py` | 10 | Role-based access control |
| `test_transactions.py` | 8 | Transaction CRUD operations |
| `test_receipts.py` | 4 | Receipt upload/list |
| `test_challenges.py` | 7 | Challenge/dispute system |
| `test_chat.py` | 5 | AI chat queries |
| `test_encryption.py` | 10 | AES-256 encryption |
| `test_audit.py` | 9 | Audit logging |
| `test_scanner.py` | 10 | Mismatch scanning |
| `test_notifications.py` | 12 | Email notifications |
| `test_ocr.py` | 10 | OCR extraction (POC) |

## Running Tests

```bash
# All tests
pytest tests/ -v

# Specific module
pytest tests/test_auth.py -v

# With coverage
pytest tests/ --cov=app --cov-report=html

# Fail on warnings
pytest tests/ -W error
```

## Test Fixtures

- `client()`: FastAPI test client
- `admin_token()`: Admin JWT token
- `resident_token()`: Resident JWT token
- `setup_database()`: Auto-init DB per test

## Adding New Tests

1. Create `tests/test_<module>.py`
2. Use `@pytest.fixture(autouse=True)` for DB setup
3. Follow pattern: Arrange, Act, Assert
4. Test both happy paths and error cases
