// API client for FlatWatch backend
const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const IDENTITY_URL = process.env.NEXT_PUBLIC_IDENTITY_URL || 'https://aadharcha.in';

// Session validation response
interface SessionValidation {
  valid: boolean;
  user?: {
    id: string;
    email: string;
    name?: string;
    role: string;
  };
}

/**
 * API call wrapper with SSO session validation
 * - Validates session before each call
 * - Auto-redirects to login if unauthenticated
 * - Includes credentials for cookie handling
 * - Adds X-User-ID header when authenticated
 */
async function apiCall<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  // Validate session first
  try {
    const validateResponse = await fetch(`${IDENTITY_URL}/api/auth/validate`, {
      method: 'GET',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
    });

    if (!validateResponse.ok || validateResponse.status === 401) {
      // Session invalid - redirect to login
      const returnUrl = encodeURIComponent(window.location.href);
      window.location.href = `${IDENTITY_URL}/login?return_url=${returnUrl}`;
      throw new Error('Unauthenticated - redirecting to login');
    }

    const sessionData: SessionValidation = await validateResponse.json();
    if (!sessionData.valid || !sessionData.user) {
      const returnUrl = encodeURIComponent(window.location.href);
      window.location.href = `${IDENTITY_URL}/login?return_url=${returnUrl}`;
      throw new Error('Unauthenticated - redirecting to login');
    }

    // Add X-User-ID header
    const headers = new Headers(options.headers || {});
    headers.append('X-User-ID', sessionData.user.id);

    // Make the actual API call with credentials
    const response = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      credentials: 'include',
      headers,
    });

    if (!response.ok) {
      throw new Error(`API call failed: ${response.statusText}`);
    }

    return response.json();
  } catch (error) {
    if (error instanceof Error && error.message.includes('redirecting')) {
      throw error;
    }
    throw error;
  }
}

export interface Transaction {
  id: number;
  amount: number;
  transaction_type: 'inflow' | 'outflow';
  description: string | null;
  vpa: string | null;
  timestamp: string;
  verified: boolean;
  entered_by_name?: string | null;
  entered_by_role?: string | null;
  approved_by_name?: string | null;
  approved_by_role?: string | null;
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
  list: async (options?: { txn_type?: string; limit?: number; offset?: number }): Promise<Transaction[]> => {
    const params = new URLSearchParams();
    if (options?.txn_type) params.append('txn_type', options.txn_type);
    if (options?.limit) params.append('limit', options.limit.toString());
    if (options?.offset) params.append('offset', options.offset.toString());
    return apiCall<Transaction[]>(`/api/transactions?${params}`);
  },

  getSummary: async (): Promise<FinancialSummary> => {
    return apiCall<FinancialSummary>('/api/transactions/summary');
  },

  sync: async () => {
    return apiCall('/api/transactions/sync', { method: 'POST' });
  },

  create: async (transaction: {
    amount: number;
    transaction_type: string;
    description?: string;
    vpa?: string;
  }): Promise<Transaction> => {
    return apiCall<Transaction>('/api/transactions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(transaction),
    });
  },
};

// Health check
export const healthCheck = async (): Promise<{ status: string; database: string; version: string }> => {
  const response = await fetch(`${API_BASE}/api/health`);
  if (!response.ok) throw new Error('Health check failed');
  return response.json();
};

// Receipts API
export interface Receipt {
  filename: string;
  upload_date: string;
  extracted_amount?: number;
  extracted_date?: string;
  extracted_vendor?: string;
  matched_transaction_id?: number;
  match_status?: 'matched' | 'partial' | 'unmatched';
}

export const receiptsApi = {
  upload: async (file: File): Promise<Receipt> => {
    const formData = new FormData();
    formData.append('file', file);

    return apiCall<Receipt>('/api/receipts/upload', {
      method: 'POST',
      body: formData,
    });
  },

  list: async (): Promise<Receipt[]> => {
    return apiCall<Receipt[]>('/api/receipts/list');
  },

  process: async (filename: string): Promise<Receipt> => {
    return apiCall<Receipt>(`/api/ocr/process/${filename}`, {
      method: 'POST',
    });
  },
};

// Chat API
export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  sources?: string[];
}

export const chatApi = {
  query: async (query: string): Promise<ChatMessage> => {
    return apiCall<ChatMessage>('/api/chat/query', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query }),
    });
  },
};

// Challenges API
export interface Challenge {
  id: number;
  transaction_id: number;
  reason: string;
  status: 'pending' | 'resolved' | 'rejected';
  created_at: string;
  resolved_at?: string;
  evidence?: string;
}

export const challengesApi = {
  create: async (transactionId: number, reason: string): Promise<Challenge> => {
    return apiCall<Challenge>('/api/challenges', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ transaction_id: transactionId, reason }),
    });
  },

  list: async (status?: string): Promise<Challenge[]> => {
    const params = status ? `?status=${status}` : '';
    return apiCall<Challenge[]>(`/api/challenges${params}`);
  },

  resolve: async (challengeId: number, evidence: string): Promise<Challenge> => {
    return apiCall<Challenge>(`/api/challenges/${challengeId}/resolve`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ evidence }),
    });
  },
};

// Notifications API
export interface Notification {
  id: number;
  type: 'daily' | 'weekly';
  sent_at: string;
  recipient_count: number;
}

export const notificationsApi = {
  send: async (type: 'daily' | 'weekly'): Promise<{ message: string }> => {
    return apiCall<{ message: string }>('/api/notifications/send', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ type }),
    });
  },

  list: async (): Promise<Notification[]> => {
    return apiCall<Notification[]>('/api/notifications/sent');
  },

  clear: async (): Promise<void> => {
    return apiCall<void>('/api/notifications/sent/clear', {
      method: 'POST',
    });
  },
};
