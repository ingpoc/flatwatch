// Transaction List - DRAMS Design
'use client';

interface Transaction {
  id: number;
  amount: number;
  transaction_type: 'inflow' | 'outflow';
  description: string | null;
  vpa: string | null;
  timestamp: string;
  verified: boolean;
}

interface TransactionListProps {
  transactions: Transaction[];
}

export function TransactionList({ transactions }: TransactionListProps) {
  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0,
    }).format(amount);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-IN', {
      day: 'numeric',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  if (transactions.length === 0) {
    return (
      <div className="w-full max-w-2xl rounded-3xl bg-white p-8 text-center shadow-[0_4px_16px_rgba(0,0,0,0.06)]">
        <p className="text-[#999]">No transactions yet</p>
      </div>
    );
  }

  return (
    <div className="w-full max-w-2xl space-y-3">
      <h2 className="text-lg font-semibold text-[#333]">Recent Transactions</h2>
      <div className="space-y-3">
        {transactions.map((txn) => (
          <div
            key={txn.id}
            className="flex items-center justify-between rounded-3xl bg-white p-4 shadow-[0_4px_16px_rgba(0,0,0,0.06)] transition-all hover:shadow-[0_8px_24px_rgba(0,0,0,0.1)] hover:-translate-y-0.5"
          >
            <div className="flex items-center gap-4">
              {/* Status indicator */}
              {!txn.verified && (
                <span className="h-2 w-2 rounded-full bg-[rgb(255,97,26)]" />
              )}
              {txn.verified && (
                <span className="h-2 w-2 rounded-full bg-[rgb(76,175,80)]" />
              )}

              {/* Transaction details */}
              <div>
                <p className="font-medium text-[#333]">
                  {txn.description || 'Transaction'}
                </p>
                <p className="text-sm text-[#999]">
                  {txn.vpa || 'Unknown'} • {formatDate(txn.timestamp)}
                </p>
              </div>
            </div>

            {/* Amount */}
            <p
              className={`text-lg font-semibold ${
                txn.transaction_type === 'inflow'
                  ? 'text-[rgb(76,175,80)]'
                  : 'text-[#333]'
              }`}
            >
              {txn.transaction_type === 'inflow' ? '+' : '-'}
              {formatCurrency(txn.amount)}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
