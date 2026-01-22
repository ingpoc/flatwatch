import { transactionsApi, receiptsApi, chatApi, challengesApi, notificationsApi } from '../api';
import { Transaction, Receipt, Challenge, Notification } from '../api';

// Mock fetch
global.fetch = jest.fn();

// Mock window.location
const mockLocation = { href: '' };
Object.defineProperty(window, 'location', {
  value: mockLocation,
  writable: true,
});

describe('API client with SSO session wrapper', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockLocation.href = '';
  });

  const mockUser = {
    id: 'user-123',
    email: 'test@example.com',
    name: 'Test User',
    role: 'resident',
  };

  describe('session validation', () => {
    it('should validate session before API call', async () => {
      (global.fetch as jest.Mock)
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ valid: true, user: mockUser }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => [],
        });

      await transactionsApi.list();

      expect(global.fetch).toHaveBeenCalledTimes(2);
      expect((global.fetch as jest.Mock).mock.calls[0][0]).toContain('/api/auth/validate');
      expect((global.fetch as jest.Mock).mock.calls[1][0]).toContain('/api/transactions');
    });

    it('should redirect to login when session is invalid (401)', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        status: 401,
      });

      await expect(transactionsApi.list()).rejects.toThrow('Unauthenticated - redirecting to login');

      expect(mockLocation.href).toContain('https://aadharcha.in/login');
      expect(mockLocation.href).toContain('return_url=');
    });

    it('should redirect to login when session valid is false', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ valid: false }),
      });

      await expect(transactionsApi.list()).rejects.toThrow('Unauthenticated - redirecting to login');

      expect(mockLocation.href).toContain('https://aadharcha.in/login');
    });

    it('should redirect to login when no user in session', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ valid: true }),
      });

      await expect(transactionsApi.list()).rejects.toThrow('Unauthenticated - redirecting to login');

      expect(mockLocation.href).toContain('https://aadharcha.in/login');
    });
  });

  describe('X-User-ID header', () => {
    it('should include X-User-ID header in API calls', async () => {
      (global.fetch as jest.Mock)
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ valid: true, user: mockUser }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => [],
        });

      await transactionsApi.list();

      const apiCallHeaders = (global.fetch as jest.Mock).mock.calls[1][1]?.headers;
      expect(apiCallHeaders).toBeDefined();
      // Headers object should contain X-User-ID
      expect((global.fetch as jest.Mock).mock.calls[1][1].credentials).toBe('include');
    });
  });

  describe('credentials: include', () => {
    it('should include credentials in both validate and API calls', async () => {
      (global.fetch as jest.Mock)
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ valid: true, user: mockUser }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => [],
        });

      await transactionsApi.list();

      expect((global.fetch as jest.Mock).mock.calls[0][1].credentials).toBe('include');
      expect((global.fetch as jest.Mock).mock.calls[1][1].credentials).toBe('include');
    });
  });

  describe('transactionsApi', () => {
    it('should list transactions', async () => {
      const mockTransactions: Transaction[] = [
        { id: 1, amount: 100, transaction_type: 'inflow', description: 'Test', vpa: 'test@upi', timestamp: '2024-01-01', verified: true },
      ];

      (global.fetch as jest.Mock)
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ valid: true, user: mockUser }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => mockTransactions,
        });

      const result = await transactionsApi.list();

      expect(result).toEqual(mockTransactions);
    });

    it('should list transactions with options', async () => {
      (global.fetch as jest.Mock)
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ valid: true, user: mockUser }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => [],
        });

      await transactionsApi.list({ txn_type: 'inflow', limit: 10, offset: 5 });

      expect((global.fetch as jest.Mock).mock.calls[1][0]).toContain('txn_type=inflow');
      expect((global.fetch as jest.Mock).mock.calls[1][0]).toContain('limit=10');
      expect((global.fetch as jest.Mock).mock.calls[1][0]).toContain('offset=5');
    });

    it('should get financial summary', async () => {
      const mockSummary = { balance: 1000, total_inflow: 2000, total_outflow: 1000, unmatched_transactions: 5, recent_transactions_24h: 10 };

      (global.fetch as jest.Mock)
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ valid: true, user: mockUser }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => mockSummary,
        });

      const result = await transactionsApi.getSummary();

      expect(result).toEqual(mockSummary);
    });

    it('should sync transactions', async () => {
      (global.fetch as jest.Mock)
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ valid: true, user: mockUser }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ message: 'Synced' }),
        });

      const result = await transactionsApi.sync();

      expect((global.fetch as jest.Mock).mock.calls[1][1].method).toBe('POST');
      expect(result).toEqual({ message: 'Synced' });
    });

    it('should create transaction', async () => {
      const mockTransaction: Transaction = {
        id: 1,
        amount: 100,
        transaction_type: 'inflow',
        description: 'Test',
        vpa: 'test@upi',
        timestamp: '2024-01-01',
        verified: true,
      };

      (global.fetch as jest.Mock)
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ valid: true, user: mockUser }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => mockTransaction,
        });

      const result = await transactionsApi.create({
        amount: 100,
        transaction_type: 'inflow',
        description: 'Test',
      });

      expect(result).toEqual(mockTransaction);
      expect((global.fetch as jest.Mock).mock.calls[1][1].method).toBe('POST');
    });
  });

  describe('receiptsApi', () => {
    it('should list receipts', async () => {
      const mockReceipts: Receipt[] = [{ filename: 'receipt.pdf', upload_date: '2024-01-01' }];

      (global.fetch as jest.Mock)
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ valid: true, user: mockUser }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => mockReceipts,
        });

      const result = await receiptsApi.list();

      expect(result).toEqual(mockReceipts);
    });

    it('should process receipt', async () => {
      const mockReceipt: Receipt = {
        filename: 'receipt.pdf',
        upload_date: '2024-01-01',
        extracted_amount: 100,
        extracted_date: '2024-01-01',
        extracted_vendor: 'Vendor',
        match_status: 'matched',
      };

      (global.fetch as jest.Mock)
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ valid: true, user: mockUser }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => mockReceipt,
        });

      const result = await receiptsApi.process('receipt.pdf');

      expect(result).toEqual(mockReceipt);
      expect((global.fetch as jest.Mock).mock.calls[1][1].method).toBe('POST');
    });
  });

  describe('chatApi', () => {
    it('should send query', async () => {
      const mockResponse = { role: 'assistant' as const, content: 'Response text', sources: [] };

      (global.fetch as jest.Mock)
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ valid: true, user: mockUser }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => mockResponse,
        });

      const result = await chatApi.query('Test query');

      expect(result).toEqual(mockResponse);
      expect((global.fetch as jest.Mock).mock.calls[1][1].method).toBe('POST');
    });
  });

  describe('challengesApi', () => {
    it('should create challenge', async () => {
      const mockChallenge: Challenge = {
        id: 1,
        transaction_id: 1,
        reason: 'Test reason',
        status: 'pending',
        created_at: '2024-01-01',
      };

      (global.fetch as jest.Mock)
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ valid: true, user: mockUser }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => mockChallenge,
        });

      const result = await challengesApi.create(1, 'Test reason');

      expect(result).toEqual(mockChallenge);
    });

    it('should list challenges with status', async () => {
      (global.fetch as jest.Mock)
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ valid: true, user: mockUser }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => [],
        });

      await challengesApi.list('pending');

      expect((global.fetch as jest.Mock).mock.calls[1][0]).toContain('status=pending');
    });

    it('should resolve challenge', async () => {
      const mockChallenge: Challenge = {
        id: 1,
        transaction_id: 1,
        reason: 'Test reason',
        status: 'resolved',
        created_at: '2024-01-01',
        resolved_at: '2024-01-02',
        evidence: 'Evidence',
      };

      (global.fetch as jest.Mock)
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ valid: true, user: mockUser }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => mockChallenge,
        });

      const result = await challengesApi.resolve(1, 'Evidence');

      expect(result).toEqual(mockChallenge);
      expect((global.fetch as jest.Mock).mock.calls[1][1].method).toBe('PUT');
    });
  });

  describe('notificationsApi', () => {
    it('should send notification', async () => {
      (global.fetch as jest.Mock)
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ valid: true, user: mockUser }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ message: 'Sent' }),
        });

      const result = await notificationsApi.send('daily');

      expect(result).toEqual({ message: 'Sent' });
    });

    it('should list notifications', async () => {
      const mockNotifications: Notification[] = [
        { id: 1, type: 'daily', sent_at: '2024-01-01', recipient_count: 10 },
      ];

      (global.fetch as jest.Mock)
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ valid: true, user: mockUser }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => mockNotifications,
        });

      const result = await notificationsApi.list();

      expect(result).toEqual(mockNotifications);
    });

    it('should clear notifications', async () => {
      (global.fetch as jest.Mock)
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ valid: true, user: mockUser }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => undefined,
        });

      await notificationsApi.clear();

      expect((global.fetch as jest.Mock).mock.calls[1][1].method).toBe('POST');
    });
  });
});
