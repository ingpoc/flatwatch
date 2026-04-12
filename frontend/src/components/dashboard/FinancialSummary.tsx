'use client';

import type { ComponentProps } from 'react';
import { Card, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

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

function SummaryCard({
  label,
  value,
  hint,
  badge,
}: {
  label: string;
  value: string | number;
  hint: string;
  badge: ComponentProps<typeof Badge>['variant'];
}) {
  return (
    <Card size="sm" className="gap-4">
      <CardHeader className="gap-3">
        <div className="flex items-center justify-between gap-3">
          <CardDescription>{label}</CardDescription>
          <Badge variant={badge}>{hint}</Badge>
        </div>
        <CardTitle className="text-2xl font-semibold tracking-[-0.04em]">{value}</CardTitle>
      </CardHeader>
    </Card>
  );
}

export function FinancialSummary({
  balance,
  totalInflow,
  totalOutflow,
  unmatched,
  recent,
}: FinancialSummaryProps) {
  return (
    <section className="space-y-4">
      <div>
        <div className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">
          Finance overview
        </div>
        <h2 className="mt-2 text-2xl font-semibold tracking-[-0.04em] text-foreground">
          Cash position and review queue
        </h2>
      </div>

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1.5fr)_repeat(2,minmax(0,1fr))]">
        <SummaryCard
          label="Current balance"
          value={formatCurrency(balance)}
          hint={balance >= 0 ? 'System online' : 'Needs review'}
          badge={balance >= 0 ? 'default' : 'destructive'}
        />
        <SummaryCard label="Total inflow" value={formatCurrency(totalInflow)} hint="Recorded income" badge="secondary" />
        <SummaryCard label="Total outflow" value={formatCurrency(totalOutflow)} hint="Recorded expenses" badge="outline" />
        <SummaryCard label="Unmatched" value={unmatched} hint="Needs evidence review" badge={unmatched > 0 ? 'secondary' : 'outline'} />
        <SummaryCard label="Last 24h" value={recent} hint="Recent transactions" badge="outline" />
      </div>
    </section>
  );
}
