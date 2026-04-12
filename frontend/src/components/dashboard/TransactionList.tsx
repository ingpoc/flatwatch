'use client';

import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
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
  return (
    <section className="space-y-4">
      <div>
        <div className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">Activity</div>
        <h2 className="mt-2 text-2xl font-semibold tracking-[-0.04em] text-foreground">Recent transactions</h2>
      </div>

      {transactions.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center text-sm text-muted-foreground">
            No transactions yet
          </CardContent>
        </Card>
      ) : (
        <div className="flex flex-col gap-3">
          {transactions.map((txn) => (
            <Card key={txn.id} size="sm">
              <CardHeader className="gap-4 sm:flex-row sm:items-start sm:justify-between">
                <div className="space-y-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant={txn.verified ? 'default' : 'secondary'}>
                      {txn.verified ? 'Verified' : 'Unverified'}
                    </Badge>
                    <Badge variant={txn.transaction_type === 'inflow' ? 'outline' : 'secondary'}>
                      {txn.transaction_type === 'inflow' ? 'Inflow' : 'Outflow'}
                    </Badge>
                  </div>
                  <div className="space-y-1">
                    <CardTitle className="text-base font-medium">
                      {txn.description || 'Transaction'}
                    </CardTitle>
                    <CardDescription>
                      {(txn.vpa || 'Unknown')} · {formatDate(txn.timestamp)}
                    </CardDescription>
                    {(txn.entered_by_name || txn.approved_by_name) ? (
                      <div className="text-xs text-muted-foreground">
                        {txn.entered_by_name ? `Entered by ${txn.entered_by_name} (${txn.entered_by_role ?? 'unknown'})` : null}
                        {txn.entered_by_name && txn.approved_by_name ? ' · ' : null}
                        {txn.approved_by_name ? `Approved by ${txn.approved_by_name} (${txn.approved_by_role ?? 'unknown'})` : null}
                      </div>
                    ) : null}
                  </div>
                </div>
                <div className="text-left sm:text-right">
                  <div className={txn.transaction_type === 'inflow' ? 'text-2xl font-semibold tracking-[-0.04em] text-primary' : 'text-2xl font-semibold tracking-[-0.04em] text-foreground'}>
                    {txn.transaction_type === 'inflow' ? '+' : '-'}
                    {formatCurrency(txn.amount)}
                  </div>
                </div>
              </CardHeader>
            </Card>
          ))}
        </div>
      )}
    </section>
  );
}
