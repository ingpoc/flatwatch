import {
  chatApi,
  challengesApi,
  notificationsApi,
  receiptsApi,
  transactionsApi,
} from '../api';

global.fetch = jest.fn();

const mockLocation = { href: '' };
Object.defineProperty(window, 'location', {
  value: mockLocation,
  writable: true,
});

const AUTH_TOKEN_KEY = 'flatwatch-auth-token';

describe('flatwatch API client', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    window.localStorage.clear();
    mockLocation.href = '';
  });

  it('redirects home when there is no bearer token', async () => {
    await expect(transactionsApi.list()).rejects.toThrow('Unauthenticated - redirecting to login');
    expect(mockLocation.href).toBe('/');
  });

  it('adds the bearer token to authenticated requests', async () => {
    window.localStorage.setItem(AUTH_TOKEN_KEY, 'demo-token');
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => [],
    });

    await transactionsApi.list();

    expect(global.fetch).toHaveBeenCalledWith(
      'http://127.0.0.1:8001/api/transactions?',
      expect.objectContaining({
        headers: expect.any(Headers),
      })
    );

    const headers = (global.fetch as jest.Mock).mock.calls[0][1].headers as Headers;
    expect(headers.get('Authorization')).toBe('Bearer demo-token');
  });

  it('clears the token and redirects home on 401 responses', async () => {
    window.localStorage.setItem(AUTH_TOKEN_KEY, 'expired-token');
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: false,
      status: 401,
      statusText: 'Unauthorized',
    });

    await expect(transactionsApi.list()).rejects.toThrow('Unauthenticated - redirecting to login');
    expect(window.localStorage.getItem(AUTH_TOKEN_KEY)).toBeNull();
    expect(mockLocation.href).toBe('/');
  });

  it('lists transactions', async () => {
    window.localStorage.setItem(AUTH_TOKEN_KEY, 'demo-token');
    const payload = [{ id: 1, amount: 100, transaction_type: 'inflow', description: null, vpa: null, timestamp: '2024-01-01', verified: true }];
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => payload,
    });

    await expect(transactionsApi.list()).resolves.toEqual(payload);
  });

  it('gets the financial summary', async () => {
    window.localStorage.setItem(AUTH_TOKEN_KEY, 'demo-token');
    const payload = { balance: 1000, total_inflow: 2000, total_outflow: 1000, unmatched_transactions: 3, recent_transactions_24h: 2 };
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => payload,
    });

    await expect(transactionsApi.getSummary()).resolves.toEqual(payload);
  });

  it('lists receipts', async () => {
    window.localStorage.setItem(AUTH_TOKEN_KEY, 'demo-token');
    const payload = {
      files: [{ filename: 'receipt.pdf', size: 512, uploaded_at: 1704067200 }],
    };
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => payload,
    });

    await expect(receiptsApi.list()).resolves.toEqual([
      {
        filename: 'receipt.pdf',
        size: 512,
        upload_date: '2024-01-01T00:00:00.000Z',
      },
    ]);
  });

  it('processes receipt OCR', async () => {
    window.localStorage.setItem(AUTH_TOKEN_KEY, 'demo-token');
    const payload = {
      message: 'Processed receipt',
      receipt: 'receipt.pdf',
      extracted: {
        amount: 8500,
        date: '2024-01-01',
        vendor: 'Water Supply Co',
      },
      matched_transaction: {
        id: 42,
      },
      flag_level: 'green',
    };
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => payload,
    });

    await expect(receiptsApi.process('receipt.pdf')).resolves.toEqual(
      expect.objectContaining({
        filename: 'receipt.pdf',
        extracted_amount: 8500,
        extracted_date: '2024-01-01',
        extracted_vendor: 'Water Supply Co',
        matched_transaction_id: 42,
        match_status: 'matched',
      })
    );
  });

  it('queries chat', async () => {
    window.localStorage.setItem(AUTH_TOKEN_KEY, 'demo-token');
    const payload = { role: 'assistant', content: 'Here are the flagged transactions.' };
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => payload,
    });

    await expect(chatApi.query('Show anomalies')).resolves.toEqual(payload);
  });

  it('creates a challenge', async () => {
    window.localStorage.setItem(AUTH_TOKEN_KEY, 'demo-token');
    const payload = { id: 3, transaction_id: 9, reason: 'Mismatch', status: 'pending', created_at: '2024-01-01' };
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => payload,
    });

    await expect(challengesApi.create(9, 'Mismatch')).resolves.toEqual(payload);
  });

  it('lists notifications', async () => {
    window.localStorage.setItem(AUTH_TOKEN_KEY, 'demo-token');
    const payload = [{ id: 1, type: 'daily', sent_at: '2024-01-01', recipient_count: 12 }];
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => payload,
    });

    await expect(notificationsApi.list()).resolves.toEqual(payload);
  });
});
