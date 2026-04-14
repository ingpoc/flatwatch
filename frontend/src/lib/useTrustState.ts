'use client';

import { createContext, createElement, useContext, useEffect, useState, type ReactNode } from 'react';
import { useWallet } from '@solana/wallet-adapter-react';
import { fetchTrustSnapshot, type TrustSnapshot } from './trust';

const DEFAULT_SNAPSHOT: TrustSnapshot = {
  state: 'no_identity',
  eligible: false,
  reason: null,
  trust: null,
};

interface TrustStateValue extends TrustSnapshot {
  loading: boolean;
  error: string | null;
}

const TrustStateContext = createContext<TrustStateValue | null>(null);

function useTrustStateLoader(subjectId?: string | null, enabled = true): TrustStateValue {
  const [snapshot, setSnapshot] = useState<TrustSnapshot>(DEFAULT_SNAPSHOT);
  const [loading, setLoading] = useState(enabled && Boolean(subjectId));
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!enabled) {
      setSnapshot(DEFAULT_SNAPSHOT);
      setLoading(false);
      setError(null);
      return;
    }

    if (!subjectId) {
      setSnapshot(DEFAULT_SNAPSHOT);
      setLoading(false);
      setError(null);
      return;
    }

    let cancelled = false;

    const run = async () => {
      try {
        setLoading(true);
        setError(null);
        const next = await fetchTrustSnapshot(subjectId);
        if (!cancelled) {
          setSnapshot(next);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load trust state.');
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    void run();

    return () => {
      cancelled = true;
    };
  }, [enabled, subjectId]);

  return {
    ...snapshot,
    loading,
    error,
  };
}

export function TrustStateProvider({ children }: { children: ReactNode }) {
  const { publicKey } = useWallet();
  const value = useTrustStateLoader(publicKey?.toBase58() ?? null);

  return createElement(TrustStateContext.Provider, { value }, children);
}

export function useTrustState(subjectId?: string | null) {
  const context = useContext(TrustStateContext);
  const normalizedSubjectId = subjectId ?? null;
  const contextMatchesSubject =
    context !== null &&
    normalizedSubjectId !== null &&
    context.trust?.wallet_address === normalizedSubjectId;
  const shouldUseContext = context !== null && (normalizedSubjectId === null || contextMatchesSubject);
  const fallback = useTrustStateLoader(normalizedSubjectId, !shouldUseContext);
  return shouldUseContext ? context : fallback;
}
