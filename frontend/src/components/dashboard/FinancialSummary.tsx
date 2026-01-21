// Financial Summary Card - DRAMS Design
'use client';

interface FinancialSummaryProps {
  balance: number;
  totalInflow: number;
  totalOutflow: number;
  unmatched: number;
  recent: number;
}

export function FinancialSummary({
  balance,
  totalInflow,
  totalOutflow,
  unmatched,
  recent,
}: FinancialSummaryProps) {
  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0,
    }).format(amount);
  };

  return (
    <div className="w-full max-w-2xl space-y-4">
      {/* Main Balance - Hero Card */}
      <div className="w-full rounded-3xl bg-white p-8 shadow-[0_4px_16px_rgba(0,0,0,0.06)] transition-all hover:shadow-[0_8px_24px_rgba(0,0,0,0.1)]">
        <p className="text-sm text-[#999] uppercase tracking-wide">Current Balance</p>
        <p className={`text-5xl font-semibold tracking-tight ${balance >= 0 ? 'text-[#333]' : 'text-[rgb(255,97,26)]'}`}>
          {formatCurrency(balance)}
        </p>
      </div>

      {/* Inflow/Outflow Cards */}
      <div className="grid grid-cols-2 gap-4">
        <div className="rounded-3xl bg-white p-6 shadow-[0_4px_16px_rgba(0,0,0,0.06)] transition-all hover:shadow-[0_8px_24px_rgba(0,0,0,0.1)]">
          <p className="text-sm text-[#999]">Total Inflow</p>
          <p className="text-2xl font-semibold text-[#333]">{formatCurrency(totalInflow)}</p>
        </div>
        <div className="rounded-3xl bg-white p-6 shadow-[0_4px_16px_rgba(0,0,0,0.06)] transition-all hover:shadow-[0_8px_24px_rgba(0,0,0,0.1)]">
          <p className="text-sm text-[#999]">Total Outflow</p>
          <p className="text-2xl font-semibold text-[#333]">{formatCurrency(totalOutflow)}</p>
        </div>
      </div>

      {/* Status Indicators */}
      <div className="flex gap-4">
        <div className="flex-1 rounded-full bg-[rgb(238,238,238)] px-4 py-3">
          <div className="flex items-center justify-between">
            <span className="text-sm text-[#999]">Unmatched</span>
            <span className={`text-sm font-semibold ${unmatched > 0 ? 'text-[rgb(255,97,26)]' : 'text-[#333]'}`}>
              {unmatched}
            </span>
          </div>
        </div>
        <div className="flex-1 rounded-full bg-[rgb(238,238,238)] px-4 py-3">
          <div className="flex items-center justify-between">
            <span className="text-sm text-[#999]">Last 24h</span>
            <span className="text-sm font-semibold text-[#333]">{recent}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
