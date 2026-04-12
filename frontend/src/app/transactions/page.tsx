'use client';

import { useEffect, useState } from 'react';
import { useWallet } from '@solana/wallet-adapter-react';
import { PageLayout } from '@/components/layout/PageLayout';
import { TrustPanel } from '@/components/trust/TrustPanel';
import { TransactionList } from '@/components/dashboard/TransactionList';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Spinner } from '@/components/ui/spinner';
import { ProtectedRoute } from '@/lib/ProtectedRoute';
import { transactionsApi, type Transaction } from '@/lib/api';
import { useTrustState } from '@/lib/useTrustState';

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
      setError('Failed to load transactions.');
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
      setError('Sync failed.');
      setSyncing(false);
    }
  };

  if (loading) {
    return (
      <div className="premium-shell flex min-h-screen items-center justify-center px-4">
        <Card className="w-full max-w-md">
          <CardContent className="flex items-center justify-center gap-3 py-10 text-muted-foreground">
            <Spinner />
            Loading transactions…
          </CardContent>
        </Card>
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
        <Button type="button" variant="secondary" onClick={handleSync} disabled={syncing}>
          {syncing ? 'Syncing…' : 'Sync now'}
        </Button>
      </div>

      {error ? (
        <Card className="border-destructive/20">
          <CardContent className="py-4 text-sm text-destructive">{error}</CardContent>
        </Card>
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
