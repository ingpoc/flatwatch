// Dashboard page - Shame Dashboard for FlatWatch
'use client';

import { useEffect, useState } from 'react';
import { FinancialSummary } from '@/components/dashboard/FinancialSummary';
import { TransactionList } from '@/components/dashboard/TransactionList';
import { transactionsApi, healthCheck } from '@/lib/api';

interface Summary {
  balance: number;
  total_inflow: number;
  total_outflow: number;
  unmatched_transactions: number;
  recent_transactions_24h: number;
}

interface Transaction {
  id: number;
  amount: number;
  transaction_type: 'inflow' | 'outflow';
  description: string | null;
  vpa: string | null;
  timestamp: string;
  verified: boolean;
}

export default function DashboardPage() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // For POC, use mock auth
  const mockToken = 'mock_token';

  useEffect(() => {
    loadData();

    // Refresh every 30 seconds
    const interval = setInterval(loadData, 30000);
    return () => clearInterval(interval);
  }, []);

  const loadData = async () => {
    try {
      setError(null);

      // Load summary
      const summaryData = await transactionsApi.getSummary(mockToken);
      setSummary(summaryData);

      // Load recent transactions
      const txns = await transactionsApi.list(mockToken, { limit: 10 });
      setTransactions(txns);

      setLoading(false);
    } catch (err) {
      setError('Failed to load data');
      setLoading(false);
    }
  };

  const handleSync = async () => {
    try {
      await transactionsApi.sync(mockToken);
      loadData();
    } catch (err) {
      setError('Sync failed');
    }
  };

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-white">
        <div className="flex items-center gap-2">
          <span className="h-3 w-3 animate-pulse rounded-full bg-[rgb(255,97,26)]" />
          <span className="text-[#999]">Loading...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-white">
        <div className="text-center">
          <p className="text-[rgb(255,97,26)]">{error}</p>
          <button
            onClick={loadData}
            className="mt-4 h-12 rounded-full bg-[rgb(255,97,26)] px-6 text font-medium text-white shadow-[0_2px_8px_rgba(255,97,26,0.3)] transition-all hover:shadow-[0_4px_12px_rgba(255,97,26,0.4)]"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-white px-6 py-12">
      <main className="mx-auto max-w-2xl space-y-12">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-4xl font-semibold tracking-tight text-[#333]">
              FlatWatch
            </h1>
            <p className="text-lg text-[#999]">Society Cash Tracker</p>
          </div>
          <button
            onClick={handleSync}
            className="h-10 rounded-full bg-[rgb(238,238,238)] px-4 text-sm font-medium text-[#333] transition-all hover:bg-[rgb(232,232,232)]"
          >
            Sync Now
          </button>
        </div>

        {/* Financial Summary */}
        {summary && (
          <FinancialSummary
            balance={summary.balance}
            totalInflow={summary.total_inflow}
            totalOutflow={summary.total_outflow}
            unmatched={summary.unmatched_transactions}
            recent={summary.recent_transactions_24h}
          />
        )}

        {/* Transaction List */}
        <TransactionList transactions={transactions} />

        {/* Footer status */}
        <div className="flex items-center justify-center gap-2 rounded-full bg-[rgb(238,238,238)] px-4 py-2">
          <span className="h-2 w-2 rounded-full bg-[rgb(76,175,80)]" />
          <span className="text-sm text-[#999]">System online • Auto-refresh every 30s</span>
        </div>
      </main>
    </div>
  );
}
