'use client';

import { useEffect, useState, type ChangeEvent } from 'react';
import { CheckCircle2, FileText, ScanSearch } from 'lucide-react';
import { useWallet } from '@solana/wallet-adapter-react';
import { PageLayout } from '@/components/layout/PageLayout';
import { TrustPanel } from '@/components/trust/TrustPanel';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Empty, EmptyContent, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from '@/components/ui/empty';
import { Spinner } from '@/components/ui/spinner';
import { ProtectedRoute } from '@/lib/ProtectedRoute';
import { receiptsApi, type Receipt } from '@/lib/api';
import { useTrustState } from '@/lib/useTrustState';

function getMatchBadge(status?: Receipt['match_status']) {
  switch (status) {
    case 'matched':
      return { label: 'Matched', variant: 'default' as const };
    case 'partial':
      return { label: 'Partial match', variant: 'secondary' as const };
    case 'unmatched':
      return { label: 'Unmatched', variant: 'destructive' as const };
    default:
      return { label: 'Uploaded', variant: 'outline' as const };
  }
}

function ReceiptsContent() {
  const { publicKey } = useWallet();
  const trust = useTrustState(publicKey?.toBase58() ?? null);
  const [receipts, setReceipts] = useState<Receipt[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fileInputKey, setFileInputKey] = useState(0);

  const loadReceipts = async () => {
    try {
      setError(null);
      const data = await receiptsApi.list();
      setReceipts(Array.isArray(data) ? data : []);
    } catch {
      setError('Failed to load receipts.');
      setReceipts([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadReceipts();
  }, []);

  const handleFileUpload = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }

    if (trust.state !== 'verified') {
      setError(trust.reason || 'Complete AadhaarChain verification before uploading evidence.');
      return;
    }

    setUploading(true);
    try {
      await receiptsApi.upload(file);
      setFileInputKey((current) => current + 1);
      await loadReceipts();
    } catch {
      setError('Upload failed.');
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
            : receipt,
        ),
      );
    } catch {
      setError('OCR processing failed.');
    }
  };

  if (loading) {
    return (
      <div className="premium-shell flex min-h-screen items-center justify-center px-4">
        <Card className="w-full max-w-md">
          <CardContent className="flex items-center justify-center gap-3 py-10 text-muted-foreground">
            <Spinner />
            Loading receipts…
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <PageLayout title="Receipts" description="Upload evidence, process OCR, and reconcile receipts with transaction activity.">
      <TrustPanel
        state={trust.state}
        loading={trust.loading}
        error={trust.error}
        reason={trust.reason}
        walletConnected={Boolean(publicKey)}
        actionLabel={publicKey ? 'Review trust in AadhaarChain' : null}
      />

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">Evidence intake</div>
          <p className="mt-1 text-sm text-muted-foreground">
            Verified trust unlocks receipt uploads and OCR-assisted matching.
          </p>
        </div>
        <label className="inline-flex">
          <input
            key={fileInputKey}
            type="file"
            accept="image/*,.pdf"
            className="hidden"
            onChange={handleFileUpload}
            disabled={uploading || trust.state !== 'verified'}
          />
          <span className="inline-flex">
            <Button type="button" disabled={uploading || trust.state !== 'verified'}>
              {uploading ? 'Uploading…' : trust.state === 'verified' ? 'Upload receipt' : 'Trust required'}
            </Button>
          </span>
        </label>
      </div>

      {error ? (
        <Card className="border-destructive/20">
          <CardContent className="py-4 text-sm text-destructive">{error}</CardContent>
        </Card>
      ) : null}

      {receipts.length === 0 ? (
        <Card>
          <CardContent className="py-0">
            <Empty className="border-border py-12">
              <EmptyHeader>
                <EmptyMedia variant="icon">
                  <FileText className="size-5" />
                </EmptyMedia>
                <EmptyTitle>No receipts uploaded</EmptyTitle>
                <EmptyDescription>
                  Start with a verified trust state, then upload evidence to build the reconciliation trail.
                </EmptyDescription>
              </EmptyHeader>
              <EmptyContent />
            </Empty>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 lg:grid-cols-2">
          {receipts.map((receipt) => {
            const match = getMatchBadge(receipt.match_status);

            return (
              <Card key={receipt.filename} size="sm">
                <CardHeader className="gap-4">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0 space-y-1">
                      <CardTitle className="truncate text-base font-medium">{receipt.filename}</CardTitle>
                      <CardDescription>
                        {new Date(receipt.upload_date).toLocaleDateString()}
                      </CardDescription>
                    </div>
                    <Badge variant={match.variant}>{match.label}</Badge>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4 pt-0">
                  {receipt.extracted_amount ? (
                    <div className="flex flex-wrap gap-2 text-sm text-muted-foreground">
                      <Badge variant="outline">₹{receipt.extracted_amount}</Badge>
                      {receipt.extracted_vendor ? <Badge variant="outline">{receipt.extracted_vendor}</Badge> : null}
                      {receipt.extracted_date ? <Badge variant="outline">{receipt.extracted_date}</Badge> : null}
                      {receipt.matched_transaction_id ? (
                        <Badge variant="default">TXN #{receipt.matched_transaction_id}</Badge>
                      ) : null}
                    </div>
                  ) : null}

                  {!receipt.extracted_amount ? (
                    <Button
                      type="button"
                      variant={trust.state === 'verified' ? 'secondary' : 'outline'}
                      disabled={trust.state !== 'verified'}
                      onClick={() => void handleProcessOCR(receipt.filename)}
                    >
                      <ScanSearch className="size-4" />
                      {trust.state === 'verified' ? 'Process OCR' : 'Trust required'}
                    </Button>
                  ) : null}
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      <Card size="sm">
        <CardContent className="flex items-center justify-center gap-2 py-4 text-sm text-muted-foreground">
          <CheckCircle2 className="size-4 text-primary" />
          Evidence pipeline online
        </CardContent>
      </Card>
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
