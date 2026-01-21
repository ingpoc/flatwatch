// API client for FlatWatch backend
const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface Transaction {
  id: number;
  amount: number;
  transaction_type: 'inflow' | 'outflow';
  description: string | null;
  vpa: string | null;
  timestamp: string;
  verified: boolean;
}

interface FinancialSummary {
  balance: number;
  total_inflow: number;
  total_outflow: number;
  unmatched_transactions: number;
  recent_transactions_24h: number;
}

interface AuthResponse {
  access_token: string;
  token_type: string;
  user: {
    id: number;
    email: string;
    name: string | null;
    role: string;
  };
}

// Auth API
export const authApi = {
  login: async (email: string, password: string): Promise<AuthResponse> => {
    const response = await fetch(`${API_BASE}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    if (!response.ok) throw new Error('Login failed');
    return response.json();
  },

  signup: async (email: string, password: string, name?: string): Promise<AuthResponse> => {
    const response = await fetch(`${API_BASE}/api/auth/signup`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password, name }),
    });
    if (!response.ok) throw new Error('Signup failed');
    return response.json();
  },
};

// Transactions API
export const transactionsApi = {
  list: async (token: string, options?: { txn_type?: string; limit?: number; offset?: number }): Promise<Transaction[]> => {
    const params = new URLSearchParams();
    if (options?.txn_type) params.append('txn_type', options.txn_type);
    if (options?.limit) params.append('limit', options.limit.toString());
    if (options?.offset) params.append('offset', options.offset.toString());

    const response = await fetch(`${API_BASE}/api/transactions?${params}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!response.ok) throw new Error('Failed to fetch transactions');
    return response.json();
  },

  getSummary: async (token: string): Promise<FinancialSummary> => {
    const response = await fetch(`${API_BASE}/api/transactions/summary`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!response.ok) throw new Error('Failed to fetch summary');
    return response.json();
  },

  sync: async (token: string) => {
    const response = await fetch(`${API_BASE}/api/transactions/sync`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!response.ok) throw new Error('Sync failed');
    return response.json();
  },

  create: async (token: string, transaction: {
    amount: number;
    transaction_type: string;
    description?: string;
    vpa?: string;
  }): Promise<Transaction> => {
    const response = await fetch(`${API_BASE}/api/transactions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(transaction),
    });
    if (!response.ok) throw new Error('Failed to create transaction');
    return response.json();
  },
};

// Health check
export const healthCheck = async (): Promise<{ status: string; database: string; version: string }> => {
  const response = await fetch(`${API_BASE}/api/health`);
  if (!response.ok) throw new Error('Health check failed');
  return response.json();
};
