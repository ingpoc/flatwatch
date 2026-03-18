'use client';

import { StatCard } from '@/lib/portfolio-ui';

interface FinancialSummaryProps {
  balance: number;
  totalInflow: number;
  totalOutflow: number;
  unmatched: number;
  recent: number;
}

function formatCurrency(amount: number) {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(amount);
}

export function FinancialSummary({
  balance,
  totalInflow,
  totalOutflow,
  unmatched,
  recent,
}: FinancialSummaryProps) {
  return (
    <div className="grid gap-4 lg:grid-cols-[minmax(0,1.5fr)_repeat(2,minmax(0,1fr))]">
      <StatCard
        label="Current balance"
        value={formatCurrency(balance)}
        hint={balance >= 0 ? 'System online' : 'Negative balance detected'}
        tone={balance >= 0 ? 'success' : 'error'}
      />
      <StatCard label="Total inflow" value={formatCurrency(totalInflow)} hint="Recorded income" tone="success" />
      <StatCard label="Total outflow" value={formatCurrency(totalOutflow)} hint="Recorded expenses" tone="warning" />
      <StatCard label="Unmatched" value={unmatched} hint="Needs evidence review" tone={unmatched > 0 ? 'warning' : 'neutral'} />
      <StatCard label="Last 24h" value={recent} hint="Recent transactions" tone="info" />
    </div>
  );
}
