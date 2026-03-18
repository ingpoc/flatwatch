'use client';

import { useEffect, useState } from 'react';
import { PageLayout } from '@/components/layout/PageLayout';
import { TrustPanel } from '@/components/trust/TrustPanel';
import { TransactionList } from '@/components/dashboard/TransactionList';
import { ProtectedRoute } from '@/lib/ProtectedRoute';
import { transactionsApi, type Transaction } from '@/lib/api';
import { useTrustState } from '@/lib/useTrustState';
import { useWallet } from '@solana/wallet-adapter-react';

function TransactionsContent() {
  const { publicKey } = useWallet();
  const trust = useTrustState(publicKey?.toBase58() ?? null);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadTransactions = async () => {
    try {
      setError(null);
      const data = await transactionsApi.list({ limit: 50 });
      setTransactions(Array.isArray(data) ? data : []);
    } catch {
      setError('Failed to load transactions');
      setTransactions([]);
    } finally {
      setLoading(false);
      setSyncing(false);
    }
  };

  useEffect(() => {
    void loadTransactions();
  }, []);

  const handleSync = async () => {
    setSyncing(true);
    try {
      await transactionsApi.sync();
      await loadTransactions();
    } catch {
      setError('Sync failed');
      setSyncing(false);
    }
  };

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-white">
        <div className="flex items-center gap-2">
          <span className="h-3 w-3 animate-pulse rounded-full bg-[rgb(255,97,26)]" />
          <span className="text-[#999]">Loading transactions...</span>
        </div>
      </div>
    );
  }

  return (
    <PageLayout title="Transactions" description="Review society inflow and outflow activity in one place.">
      <TrustPanel
        state={trust.state}
        loading={trust.loading}
        error={trust.error}
        reason={trust.reason}
        walletConnected={Boolean(publicKey)}
        actionLabel={publicKey ? 'Review trust in AadhaarChain' : null}
      />

      <div className="flex justify-end">
        <button
          onClick={handleSync}
          disabled={syncing}
          className={`h-10 rounded-full px-4 text-sm font-medium transition-all active:scale-95 ${
            syncing
              ? 'cursor-not-allowed bg-[rgb(238,238,238)] text-[#999]'
              : 'bg-[rgb(238,238,238)] text-[#333] hover:bg-[rgb(232,232,232)]'
          }`}
        >
          {syncing ? 'Syncing...' : 'Sync Now'}
        </button>
      </div>

      {error ? (
        <div className="rounded-2xl border border-[rgba(194,65,12,0.2)] bg-[rgba(255,247,237,0.9)] px-5 py-4 text-sm text-[rgb(194,65,12)]">
          {error}
        </div>
      ) : null}

      <TransactionList transactions={transactions} />
    </PageLayout>
  );
}

export default function TransactionsPage() {
  return (
    <ProtectedRoute>
      <TransactionsContent />
    </ProtectedRoute>
  );
}
