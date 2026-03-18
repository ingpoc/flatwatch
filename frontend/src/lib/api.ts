// API client for FlatWatch backend
const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8001';
const AUTH_TOKEN_KEY = 'flatwatch-auth-token';

function getAuthToken(): string | null {
  if (typeof window === 'undefined') {
    return null;
  }
  return window.localStorage.getItem(AUTH_TOKEN_KEY);
}

/**
 * API call wrapper with local bearer token auth
 */
async function apiCall<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getAuthToken();
  if (!token) {
    window.location.href = '/';
    throw new Error('Unauthenticated - redirecting to login');
  }

  const headers = new Headers(options.headers || {});
  headers.set('Authorization', `Bearer ${token}`);

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  if (response.status === 401) {
    window.localStorage.removeItem(AUTH_TOKEN_KEY);
    window.location.href = '/';
    throw new Error('Unauthenticated - redirecting to login');
  }

  if (!response.ok) {
    throw new Error(`API call failed: ${response.statusText}`);
  }

  return response.json();
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

interface ChatQueryResponse {
  query: string;
  response: string;
  session_id?: string;
  timestamp?: string;
  sources?: string[];
}

export type AgentAuthMode = 'api_key' | 'local_cli' | 'bedrock' | 'vertex' | 'azure' | 'unavailable';
export type PortfolioTrustState =
  | 'no_identity'
  | 'identity_present_unverified'
  | 'verified'
  | 'manual_review'
  | 'revoked_or_blocked';

export interface UsageSnapshot {
  requests_used: number;
  requests_limit: number;
  period_start: string;
  period_end: string;
  estimated_cost_usd: number;
}

export interface AgentRuntimeSnapshot {
  app_id: 'flatwatch' | 'ondc-buyer' | 'ondc-seller';
  auth_mode: AgentAuthMode;
  model: string;
  runtime_available: boolean;
  agent_access: boolean;
  trust_state: PortfolioTrustState;
  trust_required_for_write: boolean;
  mode: 'blocked' | 'read_only' | 'full';
  usage: UsageSnapshot;
  allowed_capabilities: string[];
  blocked_reason: string | null;
}

export interface AgentSessionSummary {
  app_id: 'flatwatch' | 'ondc-buyer' | 'ondc-seller';
  session_id: string;
  sdk_session_id: string | null;
  subject_id: string;
  trust_state: PortfolioTrustState;
  mode: 'blocked' | 'read_only' | 'full';
  allowed_capabilities: string[];
  created_at: string;
  updated_at: string;
}

export type AgentStreamEvent =
  | { type: 'init'; session_id: string; sdk_session_id: string | null; mode: AgentSessionSummary['mode'] }
  | { type: 'assistant_delta'; content: string; timestamp: number }
  | { type: 'tool_call'; tool: string; status?: string; timestamp: number }
  | { type: 'tool_result'; tool: string; status?: string; content?: string; timestamp: number }
  | { type: 'result'; content: string; timestamp: number; sdk_session_id?: string | null; estimated_cost_usd?: number }
  | { type: 'error'; error: string; timestamp: number }
  | { type: 'usage'; usage: UsageSnapshot; timestamp: number };

async function streamEventSource(
  endpoint: string,
  options: RequestInit,
  onEvent: (event: AgentStreamEvent) => void
) {
  const response = await fetch(`${API_BASE}${endpoint}`, options);
  if (!response.ok) {
    throw new Error(`API call failed: ${response.statusText}`);
  }

  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error('No response body');
  }

  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() ?? '';

    for (const line of lines) {
      if (!line.startsWith('data:')) continue;
      const data = line.replace(/^data:\s*/, '').trim();
      if (!data || data === '[DONE]') continue;
      onEvent(JSON.parse(data) as AgentStreamEvent);
    }
  }
}

export const chatApi = {
  query: async (query: string): Promise<ChatMessage> => {
    const response = await apiCall<ChatQueryResponse>('/api/chat/query', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query }),
    });

    return {
      role: 'assistant',
      content: response.response ?? (response as unknown as ChatMessage).content,
      sources: response.sources ?? (response as unknown as ChatMessage).sources,
    };
  },
};

export const agentApi = {
  getRuntime: async (appId: 'flatwatch' | 'ondc-buyer' | 'ondc-seller', walletAddress?: string | null) => {
    return apiCall<AgentRuntimeSnapshot>(`/api/agent/runtime?app=${appId}`, {
      headers: walletAddress ? { 'X-Wallet-Address': walletAddress } : undefined,
    });
  },

  createSession: async (
    appId: 'flatwatch' | 'ondc-buyer' | 'ondc-seller',
    payload: { task_type: string; context: Record<string, unknown>; resume_session_id?: string },
    walletAddress?: string | null
  ) => {
    return apiCall<AgentSessionSummary>(`/api/agent/${appId}/sessions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(walletAddress ? { 'X-Wallet-Address': walletAddress } : {}),
      },
      body: JSON.stringify(payload),
    });
  },

  streamMessage: async (
    appId: 'flatwatch' | 'ondc-buyer' | 'ondc-seller',
    payload: { session_id: string; message: string },
    onEvent: (event: AgentStreamEvent) => void,
    walletAddress?: string | null
  ) => {
    const token = getAuthToken();
    if (!token) {
      throw new Error('Unauthenticated - redirecting to login');
    }
    await streamEventSource(
      `/api/agent/${appId}/messages`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
          ...(walletAddress ? { 'X-Wallet-Address': walletAddress } : {}),
        },
        body: JSON.stringify(payload),
      },
      onEvent,
    );
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
