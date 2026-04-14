'use client';

import { createContext, useCallback, useContext, useEffect, useMemo, useState, ReactNode } from 'react';
import { resolveFlatwatchApiBase } from './apiBase';

const API_BASE = resolveFlatwatchApiBase();
const AUTH_TOKEN_KEY = 'flatwatch-auth-token';
const DEV_LOGIN_EMAIL = process.env.NEXT_PUBLIC_DEV_USER_EMAIL || 'resident@flatwatch.test';
const DEV_LOGIN_PASSWORD = process.env.NEXT_PUBLIC_DEV_USER_PASSWORD || 'dev-local';
const BACKEND_UNAVAILABLE_MESSAGE = `FlatWatch backend unavailable at ${API_BASE}. Start the local API and try again.`;

export interface User {
  id: string;
  email: string;
  name?: string;
  role: string;
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  error: string | null;
  validateSession: () => Promise<boolean>;
  login: () => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
}

interface AuthProviderProps {
  children: ReactNode;
}

function formatAuthError(error: unknown): string {
  if (error instanceof TypeError && error.message.includes('Failed to fetch')) {
    return BACKEND_UNAVAILABLE_MESSAGE;
  }

  return error instanceof Error ? error.message : 'Unknown error';
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const validateSession = useCallback(async (): Promise<boolean> => {
    const token = window.localStorage.getItem(AUTH_TOKEN_KEY);
    if (!token) {
      setUser(null);
      setError(null);
      setLoading(false);
      return false;
    }

    try {
      const response = await fetch(`${API_BASE}/api/auth/verify`, {
        method: 'GET',
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        if (response.status === 401) {
          window.localStorage.removeItem(AUTH_TOKEN_KEY);
          setUser(null);
          setError(null);
          return false;
        }
        throw new Error(`Session validation failed: ${response.statusText}`);
      }

      const data = await response.json();

      if (data.valid && data.user) {
        setUser({
          id: data.user.id,
          email: data.user.email,
          name: data.user.name,
          role: data.user.role,
        });
        setError(null);
        return true;
      }

      setUser(null);
      return false;
    } catch (err) {
      setError(formatAuthError(err));
      setUser(null);
      return false;
    } finally {
      setLoading(false);
    }
  }, []);

  const login = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch(`${API_BASE}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: DEV_LOGIN_EMAIL,
          password: DEV_LOGIN_PASSWORD,
        }),
      });

      if (!response.ok) {
        throw new Error('Login failed');
      }

      const data = await response.json();
      window.localStorage.setItem(AUTH_TOKEN_KEY, data.access_token);
      setUser({
        id: String(data.user.id),
        email: data.user.email,
        name: data.user.name ?? undefined,
        role: data.user.role,
      });
    } catch (err) {
      setError(formatAuthError(err));
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  const logout = useCallback(async () => {
    window.localStorage.removeItem(AUTH_TOKEN_KEY);
    setUser(null);
    window.location.href = '/';
  }, []);

  useEffect(() => {
    void validateSession();
  }, [validateSession]);

  const value: AuthContextType = useMemo(() => ({
    user,
    loading,
    error,
    validateSession,
    login,
    logout,
  }), [user, loading, error, validateSession, login, logout]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
