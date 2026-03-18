// Receipt Snap - Upload and manage receipts
'use client';

import { useEffect, useState } from 'react';
import { PageLayout } from '@/components/layout/PageLayout';
import { TrustPanel } from '@/components/trust/TrustPanel';
import { ProtectedRoute } from '@/lib/ProtectedRoute';
import { receiptsApi } from '@/lib/api';
import type { Receipt } from '@/lib/api';
import { useTrustState } from '@/lib/useTrustState';
import { useWallet } from '@solana/wallet-adapter-react';

function ReceiptsContent() {
  const { publicKey } = useWallet();
  const trust = useTrustState(publicKey?.toBase58() ?? null);
  const [receipts, setReceipts] = useState<Receipt[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fileInputKey, setFileInputKey] = useState(0);

  useEffect(() => {
    loadReceipts();
  }, []);

  const loadReceipts = async () => {
    try {
      setError(null);
      const data = await receiptsApi.list();
      setReceipts(Array.isArray(data) ? data : []);
      setLoading(false);
    } catch {
      setError('Failed to load receipts');
      setReceipts([]);
      setLoading(false);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (trust.state !== 'verified') {
      setError(trust.reason || 'Complete AadhaarChain verification before uploading evidence.');
      return;
    }

    setUploading(true);
    try {
      await receiptsApi.upload(file);
      setFileInputKey(prev => prev + 1);
      await loadReceipts();
    } catch {
      setError('Upload failed');
    } finally {
      setUploading(false);
    }
  };

  const handleProcessOCR = async (filename: string) => {
    if (trust.state !== 'verified') {
      setError(trust.reason || 'Complete AadhaarChain verification before processing evidence.');
      return;
    }

    try {
      const processedReceipt = await receiptsApi.process(filename);
      setReceipts((current) =>
        current.map((receipt) =>
          receipt.filename === filename
            ? {
                ...receipt,
                ...processedReceipt,
                filename: receipt.filename,
                upload_date: receipt.upload_date,
              }
            : receipt
        )
      );
    } catch {
      setError('OCR processing failed');
    }
  };

  const getMatchStatusColor = (status?: string) => {
    switch (status) {
      case 'matched': return 'bg-[rgb(76,175,80)]';
      case 'partial': return 'bg-[rgb(255,152,0)]';
      case 'unmatched': return 'bg-[rgb(244,67,54)]';
      default: return 'bg-[rgb(158,158,158)]';
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

  return (
    <PageLayout title="Receipt Snap" description="Upload and verify receipts">
      <TrustPanel
        state={trust.state}
        loading={trust.loading}
        error={trust.error}
        reason={trust.reason}
        walletConnected={Boolean(publicKey)}
        actionLabel={publicKey ? 'Resolve evidence trust in AadhaarChain' : null}
      />

      {/* Error message */}
      {error && (
        <div className="rounded-2xl bg-[rgb(255,243,224)] p-4 text-[rgb(255,97,26)]">
          {error}
        </div>
      )}

      {/* Upload Section */}
      <div className="w-full rounded-3xl bg-white p-8 shadow-[0_4px_16px_rgba(0,0,0,0.06)]">
        <h2 className="text-xl font-medium text-[#333]">Upload Receipt</h2>
        <p className="mt-2 text-sm text-[#999]">Supports PDF, PNG, JPG, Excel, CSV</p>

        <div className="mt-6">
          <input
            key={fileInputKey}
            type="file"
            accept=".pdf,.png,.jpg,.jpeg,.xlsx,.xls,.csv"
            onChange={handleFileUpload}
            disabled={uploading || trust.state !== 'verified'}
            className="hidden"
            id="file-upload"
          />
          <label
            htmlFor="file-upload"
            className={`flex h-12 w-full items-center justify-center rounded-full px-6 font-medium text-white transition-all ${
              uploading || trust.state !== 'verified'
                ? 'cursor-not-allowed bg-[rgb(238,238,238)] text-[#999]'
                : 'cursor-pointer bg-[rgb(255,97,26)] shadow-[0_2px_8px_rgba(255,97,26,0.3)] hover:shadow-[0_4px_12px_rgba(255,97,26,0.4)] active:scale-95'
            }`}
          >
            {uploading
              ? 'Uploading...'
              : trust.state !== 'verified'
                ? 'Verified trust required to upload'
                : 'Choose File to Upload'}
          </label>
        </div>
      </div>

      {/* Receipts List */}
      <div>
        <h2 className="text-xl font-medium text-[#333]">Receipts ({receipts.length})</h2>

        {receipts.length === 0 ? (
          <div className="mt-6 text-center text-[#999]">No receipts uploaded yet</div>
        ) : (
          <div className="mt-4 space-y-3">
            {receipts.map((receipt) => (
              <div
                key={receipt.filename}
                className="rounded-2xl bg-white p-5 shadow-[0_4px_16px_rgba(0,0,0,0.06)] transition-all hover:shadow-[0_8px_24px_rgba(0,0,0,0.1)]"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <h3 className="font-medium text-[#333] truncate">{receipt.filename}</h3>
                      <span className={`h-2 w-2 flex-shrink-0 rounded-full ${getMatchStatusColor(receipt.match_status)}`} />
                    </div>
                    <p className="mt-1 text-sm text-[#999]">
                      {new Date(receipt.upload_date).toLocaleDateString()}
                    </p>

                    {receipt.extracted_amount && (
                      <div className="mt-3 flex flex-wrap gap-x-6 gap-y-1 text-sm">
                        <span className="text-[#999]">₹{receipt.extracted_amount}</span>
                        {receipt.extracted_vendor && <span className="text-[#333]">{receipt.extracted_vendor}</span>}
                        {receipt.extracted_date && <span className="text-[#999]">{receipt.extracted_date}</span>}
                        {receipt.matched_transaction_id && <span className="text-[rgb(76,175,80)]">TXN #{receipt.matched_transaction_id}</span>}
                      </div>
                    )}
                  </div>

                  {!receipt.extracted_amount && (
                    <button
                      onClick={() => handleProcessOCR(receipt.filename)}
                      disabled={trust.state !== 'verified'}
                      className={`flex-shrink-0 h-10 rounded-full px-4 text-sm font-medium transition-all ${
                        trust.state !== 'verified'
                          ? 'cursor-not-allowed bg-[rgb(238,238,238)] text-[#999]'
                          : 'bg-[rgb(255,97,26)] text-white shadow-[0_2px_8px_rgba(255,97,26,0.3)] hover:shadow-[0_4px_12px_rgba(255,97,26,0.4)] active:scale-95'
                      }`}
                    >
                      {trust.state !== 'verified' ? 'Trust required' : 'Process'}
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Footer status */}
      <div className="flex items-center justify-center gap-2 rounded-full bg-[rgb(238,238,238)] px-4 py-3">
        <span className="h-2 w-2 rounded-full bg-[rgb(76,175,80)]" />
        <span className="text-sm text-[#999]">System online</span>
      </div>
    </PageLayout>
  );
}

export default function ReceiptsPage() {
  return (
    <ProtectedRoute>
      <ReceiptsContent />
    </ProtectedRoute>
  );
}
