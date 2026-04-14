'use client';

import { useEffect } from 'react';
import { CheckCircle2 } from 'lucide-react';
import { useWallet } from '@solana/wallet-adapter-react';
import { PageLayout } from '@/components/layout/PageLayout';
import { FinancialSummary } from '@/components/dashboard/FinancialSummary';
import { TransactionList } from '@/components/dashboard/TransactionList';
import { TrustPanel } from '@/components/trust/TrustPanel';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Spinner } from '@/components/ui/spinner';
import { ProtectedRoute } from '@/lib/ProtectedRoute';
import { transactionsApi } from '@/lib/api';
import { useFlatwatchData } from '@/lib/useFlatwatchData';
import { useTrustState } from '@/lib/useTrustState';

function DashboardContent() {
  const { publicKey } = useWallet();
  const trust = useTrustState(publicKey?.toBase58() ?? null);
  const { dashboardSummary, dashboardTransactions, refreshDashboard, refreshTransactions } = useFlatwatchData();
  const summary = dashboardSummary.data;
  const transactions = dashboardTransactions.data;
  const error = dashboardSummary.error || dashboardTransactions.error;
  const loading = (!dashboardSummary.loaded || !dashboardTransactions.loaded) && !error;

  useEffect(() => {
    void refreshDashboard();
  }, [refreshDashboard]);

  const handleSync = async () => {
    try {
      await transactionsApi.sync();
      await Promise.all([refreshDashboard(true), refreshTransactions(true)]);
    } catch {
      // Preserve the last good dashboard state when sync fails.
    }
  };

  if (loading) {
    return (
      <div className="premium-shell flex min-h-screen items-center justify-center px-4">
        <Card className="w-full max-w-md">
          <CardContent className="flex items-center justify-center gap-3 py-10 text-muted-foreground">
            <Spinner />
            Loading dashboard…
          </CardContent>
        </Card>
      </div>
    );
  }

  if (error) {
    return (
      <div className="premium-shell flex min-h-screen items-center justify-center px-4">
        <Card className="w-full max-w-md border-destructive/20">
          <CardContent className="flex flex-col items-center gap-4 py-10 text-center">
            <p className="text-sm text-destructive">{error}</p>
            <Button type="button" onClick={() => void refreshDashboard(true)}>
              Retry
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <PageLayout title="FlatWatch" description="Track cash flow, evidence, and challenges from one trust-aware workspace.">
      <TrustPanel
        state={trust.state}
        loading={trust.loading}
        error={trust.error}
        reason={trust.reason}
        walletConnected={Boolean(publicKey)}
        actionLabel={publicKey ? 'Review trust in AadhaarChain' : null}
      />

      <div className="flex justify-end">
        <Button type="button" variant="secondary" onClick={handleSync}>
          Sync now
        </Button>
      </div>

      {summary ? (
        <FinancialSummary
          balance={summary.balance}
          totalInflow={summary.total_inflow}
          totalOutflow={summary.total_outflow}
          unmatched={summary.unmatched_transactions}
          recent={summary.recent_transactions_24h}
        />
      ) : null}

      <TransactionList transactions={transactions} />

      <Card size="sm">
        <CardContent className="flex items-center justify-center gap-2 py-4 text-sm text-muted-foreground">
          <CheckCircle2 className="size-4 text-primary" />
          System online
        </CardContent>
      </Card>
    </PageLayout>
  );
}

export default function DashboardPage() {
  return (
    <ProtectedRoute>
      <DashboardContent />
    </ProtectedRoute>
  );
}
