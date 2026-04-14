'use client';

import { createContext, useCallback, useContext, useMemo, useRef, useState, type ReactNode } from 'react';
import {
  challengesApi,
  receiptsApi,
  transactionsApi,
  type Challenge,
  type FinancialSummary,
  type Receipt,
  type Transaction,
} from './api';

const CACHE_TTL_MS = 60_000;

interface CachedResource<T> {
  data: T;
  error: string | null;
  loaded: boolean;
  loading: boolean;
  refreshing: boolean;
  loadedAt: number | null;
}

interface FlatwatchDataContextValue {
  dashboardSummary: CachedResource<FinancialSummary | null>;
  dashboardTransactions: CachedResource<Transaction[]>;
  transactions: CachedResource<Transaction[]>;
  challenges: CachedResource<Challenge[]>;
  receipts: CachedResource<Receipt[]>;
  refreshDashboard: (force?: boolean) => Promise<void>;
  refreshTransactions: (force?: boolean) => Promise<void>;
  refreshChallenges: (force?: boolean) => Promise<void>;
  refreshReceipts: (force?: boolean) => Promise<void>;
}

const FlatwatchDataContext = createContext<FlatwatchDataContextValue | null>(null);

function createValueState<T>(): CachedResource<T | null> {
  return {
    data: null,
    error: null,
    loaded: false,
    loading: false,
    refreshing: false,
    loadedAt: null,
  };
}

function createListState<T>(): CachedResource<T[]> {
  return {
    data: [],
    error: null,
    loaded: false,
    loading: false,
    refreshing: false,
    loadedAt: null,
  };
}

function isFresh(loadedAt: number | null, force = false) {
  if (force || loadedAt === null) {
    return false;
  }

  return Date.now() - loadedAt < CACHE_TTL_MS;
}

function formatError(error: unknown, fallback: string) {
  return error instanceof Error ? error.message : fallback;
}

export function FlatwatchDataProvider({ children }: { children: ReactNode }) {
  const [dashboardSummary, setDashboardSummary] = useState(createValueState<FinancialSummary>());
  const [dashboardTransactions, setDashboardTransactions] = useState(createListState<Transaction>());
  const [transactions, setTransactions] = useState(createListState<Transaction>());
  const [challenges, setChallenges] = useState(createListState<Challenge>());
  const [receipts, setReceipts] = useState(createListState<Receipt>());

  const dashboardPromiseRef = useRef<Promise<void> | null>(null);
  const transactionsPromiseRef = useRef<Promise<void> | null>(null);
  const challengesPromiseRef = useRef<Promise<void> | null>(null);
  const receiptsPromiseRef = useRef<Promise<void> | null>(null);

  const refreshDashboard = useCallback(async (force = false) => {
    if (!force && isFresh(dashboardSummary.loadedAt) && isFresh(dashboardTransactions.loadedAt)) {
      return;
    }

    if (dashboardPromiseRef.current) {
      return dashboardPromiseRef.current;
    }

    setDashboardSummary((current) => ({
      ...current,
      error: null,
      loading: !current.loaded,
      refreshing: current.loaded,
    }));
    setDashboardTransactions((current) => ({
      ...current,
      error: null,
      loading: !current.loaded,
      refreshing: current.loaded,
    }));

    dashboardPromiseRef.current = (async () => {
      try {
        const [summary, recentTransactions] = await Promise.all([
          transactionsApi.getSummary(),
          transactionsApi.list({ limit: 10 }),
        ]);
        const loadedAt = Date.now();
        setDashboardSummary({
          data: summary,
          error: null,
          loaded: true,
          loading: false,
          refreshing: false,
          loadedAt,
        });
        setDashboardTransactions({
          data: Array.isArray(recentTransactions) ? recentTransactions : [],
          error: null,
          loaded: true,
          loading: false,
          refreshing: false,
          loadedAt,
        });
      } catch (error) {
        const message = formatError(error, 'Failed to load dashboard data.');
        setDashboardSummary((current) => ({
          ...current,
          error: message,
          loading: false,
          refreshing: false,
        }));
        setDashboardTransactions((current) => ({
          ...current,
          error: message,
          loading: false,
          refreshing: false,
        }));
      } finally {
        dashboardPromiseRef.current = null;
      }
    })();

    return dashboardPromiseRef.current;
  }, [dashboardSummary.loadedAt, dashboardTransactions.loadedAt]);

  const refreshTransactions = useCallback(async (force = false) => {
    if (!force && isFresh(transactions.loadedAt)) {
      return;
    }

    if (transactionsPromiseRef.current) {
      return transactionsPromiseRef.current;
    }

    setTransactions((current) => ({
      ...current,
      error: null,
      loading: !current.loaded,
      refreshing: current.loaded,
    }));

    transactionsPromiseRef.current = (async () => {
      try {
        const next = await transactionsApi.list({ limit: 50 });
        setTransactions({
          data: Array.isArray(next) ? next : [],
          error: null,
          loaded: true,
          loading: false,
          refreshing: false,
          loadedAt: Date.now(),
        });
      } catch (error) {
        const message = formatError(error, 'Failed to load transactions.');
        setTransactions((current) => ({
          ...current,
          error: message,
          loading: false,
          refreshing: false,
        }));
      } finally {
        transactionsPromiseRef.current = null;
      }
    })();

    return transactionsPromiseRef.current;
  }, [transactions.loadedAt]);

  const refreshChallenges = useCallback(async (force = false) => {
    if (!force && isFresh(challenges.loadedAt)) {
      return;
    }

    if (challengesPromiseRef.current) {
      return challengesPromiseRef.current;
    }

    setChallenges((current) => ({
      ...current,
      error: null,
      loading: !current.loaded,
      refreshing: current.loaded,
    }));

    challengesPromiseRef.current = (async () => {
      try {
        const next = await challengesApi.list();
        setChallenges({
          data: Array.isArray(next) ? next : [],
          error: null,
          loaded: true,
          loading: false,
          refreshing: false,
          loadedAt: Date.now(),
        });
      } catch (error) {
        const message = formatError(error, 'Failed to load challenges.');
        setChallenges((current) => ({
          ...current,
          error: message,
          loading: false,
          refreshing: false,
        }));
      } finally {
        challengesPromiseRef.current = null;
      }
    })();

    return challengesPromiseRef.current;
  }, [challenges.loadedAt]);

  const refreshReceipts = useCallback(async (force = false) => {
    if (!force && isFresh(receipts.loadedAt)) {
      return;
    }

    if (receiptsPromiseRef.current) {
      return receiptsPromiseRef.current;
    }

    setReceipts((current) => ({
      ...current,
      error: null,
      loading: !current.loaded,
      refreshing: current.loaded,
    }));

    receiptsPromiseRef.current = (async () => {
      try {
        const next = await receiptsApi.list();
        setReceipts({
          data: Array.isArray(next) ? next : [],
          error: null,
          loaded: true,
          loading: false,
          refreshing: false,
          loadedAt: Date.now(),
        });
      } catch (error) {
        const message = formatError(error, 'Failed to load receipts.');
        setReceipts((current) => ({
          ...current,
          error: message,
          loading: false,
          refreshing: false,
        }));
      } finally {
        receiptsPromiseRef.current = null;
      }
    })();

    return receiptsPromiseRef.current;
  }, [receipts.loadedAt]);

  const value = useMemo<FlatwatchDataContextValue>(() => ({
    dashboardSummary,
    dashboardTransactions,
    transactions,
    challenges,
    receipts,
    refreshDashboard,
    refreshTransactions,
    refreshChallenges,
    refreshReceipts,
  }), [
    challenges,
    dashboardSummary,
    dashboardTransactions,
    receipts,
    refreshChallenges,
    refreshDashboard,
    refreshReceipts,
    refreshTransactions,
    transactions,
  ]);

  return <FlatwatchDataContext.Provider value={value}>{children}</FlatwatchDataContext.Provider>;
}

export function useFlatwatchData() {
  const context = useContext(FlatwatchDataContext);
  if (!context) {
    throw new Error('useFlatwatchData must be used within FlatwatchDataProvider');
  }
  return context;
}
