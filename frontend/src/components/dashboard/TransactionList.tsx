'use client';

import { Badge, Card } from '@/lib/portfolio-ui';
import type { Transaction } from '@/lib/api';

interface TransactionListProps {
  transactions: Transaction[];
}

function formatCurrency(amount: number) {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(amount);
}

function formatDate(dateString: string) {
  return new Date(dateString).toLocaleDateString('en-IN', {
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function TransactionList({ transactions }: TransactionListProps) {
  if (transactions.length === 0) {
    return (
      <Card className="p-8 text-center">
        <div className="text-sm text-[var(--ui-text-secondary)]">No transactions yet</div>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <div>
        <div className="text-xs font-bold uppercase tracking-[0.18em] text-[var(--ui-text-muted)]">Activity</div>
        <h2 className="mt-2 text-2xl font-bold tracking-[-0.03em] text-[var(--ui-text)]">Recent transactions</h2>
      </div>

      <div className="space-y-3">
        {transactions.map((txn) => (
          <Card key={txn.id} className="flex flex-col gap-4 p-5 sm:flex-row sm:items-start sm:justify-between">
            <div className="min-w-0 flex-1 space-y-2">
              <div className="flex flex-wrap items-center gap-2">
                <Badge tone={txn.verified ? 'success' : 'warning'}>{txn.verified ? 'Verified' : 'Unverified'}</Badge>
                <Badge tone={txn.transaction_type === 'inflow' ? 'success' : 'neutral'}>
                  {txn.transaction_type === 'inflow' ? 'Inflow' : 'Outflow'}
                </Badge>
              </div>
              <div className="text-base font-semibold text-[var(--ui-text)]">{txn.description || 'Transaction'}</div>
              <div className="text-sm text-[var(--ui-text-secondary)]">
                {(txn.vpa || 'Unknown')} · {formatDate(txn.timestamp)}
              </div>
              {(txn.entered_by_name || txn.approved_by_name) ? (
                <div className="text-xs text-[var(--ui-text-muted)]">
                  {txn.entered_by_name ? `Entered by ${txn.entered_by_name} (${txn.entered_by_role ?? 'unknown'})` : null}
                  {txn.entered_by_name && txn.approved_by_name ? ' · ' : null}
                  {txn.approved_by_name ? `Approved by ${txn.approved_by_name} (${txn.approved_by_role ?? 'unknown'})` : null}
                </div>
              ) : null}
            </div>

            <div className="text-right">
              <div
                className={
                  txn.transaction_type === 'inflow'
                    ? 'text-2xl font-bold tracking-[-0.03em] text-[var(--ui-success)]'
                    : 'text-2xl font-bold tracking-[-0.03em] text-[var(--ui-text)]'
                }
              >
                {txn.transaction_type === 'inflow' ? '+' : '-'}
                {formatCurrency(txn.amount)}
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
