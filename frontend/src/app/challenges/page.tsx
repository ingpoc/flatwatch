'use client';

import { useEffect, useMemo, useState } from 'react';
import { AlertTriangle, CheckCircle2, FileWarning } from 'lucide-react';
import { useWallet } from '@solana/wallet-adapter-react';
import { PageLayout } from '@/components/layout/PageLayout';
import { TrustPanel } from '@/components/trust/TrustPanel';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Field, FieldContent, FieldGroup, FieldLabel } from '@/components/ui/field';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { Spinner } from '@/components/ui/spinner';
import { ProtectedRoute } from '@/lib/ProtectedRoute';
import { useAuth } from '@/lib/auth';
import { challengesApi, transactionsApi } from '@/lib/api';
import type { Challenge, Transaction } from '@/lib/api';
import { useTrustState } from '@/lib/useTrustState';

function getChallengeBadge(status: Challenge['status']) {
  switch (status) {
    case 'resolved':
      return { label: 'Resolved', variant: 'default' as const };
    case 'rejected':
      return { label: 'Rejected', variant: 'destructive' as const };
    default:
      return { label: 'Pending', variant: 'secondary' as const };
  }
}

function formatCurrency(amount: number) {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(amount);
}

function ChallengesContent() {
  const { user } = useAuth();
  const { publicKey } = useWallet();
  const trust = useTrustState(publicKey?.toBase58() ?? null);
  const [challenges, setChallenges] = useState<Challenge[]>([]);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showNewForm, setShowNewForm] = useState(false);
  const [selectedTxnId, setSelectedTxnId] = useState<number | null>(null);
  const [reason, setReason] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const canResolveChallenges = user?.role === 'admin' || user?.role === 'super_admin';

  const transactionMap = useMemo(
    () => new Map(transactions.map((transaction) => [transaction.id, transaction])),
    [transactions],
  );

  const loadData = async () => {
    try {
      setError(null);
      const [challengeData, transactionData] = await Promise.all([
        challengesApi.list(),
        transactionsApi.list({ limit: 50 }),
      ]);
      setChallenges(Array.isArray(challengeData) ? challengeData : []);
      setTransactions(Array.isArray(transactionData) ? transactionData : []);
    } catch {
      setError('Failed to load challenges.');
      setChallenges([]);
      setTransactions([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadData();
  }, []);

  const handleCreateChallenge = async () => {
    if (!selectedTxnId || !reason.trim() || submitting) {
      return;
    }

    if (trust.state !== 'verified') {
      setError(trust.reason || 'Complete AadhaarChain verification before filing a challenge.');
      return;
    }

    setSubmitting(true);
    try {
      await challengesApi.create(selectedTxnId, reason.trim());
      setShowNewForm(false);
      setSelectedTxnId(null);
      setReason('');
      await loadData();
    } catch {
      setError('Failed to create challenge.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleResolve = async (challengeId: number) => {
    if (trust.state !== 'verified') {
      setError(trust.reason || 'Complete AadhaarChain verification before resolving a challenge.');
      return;
    }

    const evidence = window.prompt('Enter evidence URL:');
    if (!evidence) {
      return;
    }

    try {
      await challengesApi.resolve(challengeId, evidence);
      await loadData();
    } catch {
      setError('Failed to resolve challenge.');
    }
  };

  if (loading) {
    return (
      <div className="premium-shell flex min-h-screen items-center justify-center px-4">
        <Card className="w-full max-w-md">
          <CardContent className="flex items-center justify-center gap-3 py-10 text-muted-foreground">
            <Spinner />
            Loading challenges…
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <PageLayout title="Challenges" description="Flag suspicious activity, attach trust-backed rationale, and close investigations with evidence.">
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
          <div className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">Challenge desk</div>
          <p className="mt-1 text-sm text-muted-foreground">
            Trust verification is required before a dispute can be filed or resolved.
          </p>
        </div>
        <Button type="button" variant={showNewForm ? 'secondary' : 'default'} onClick={() => setShowNewForm((current) => !current)}>
          {showNewForm ? 'Close form' : 'New challenge'}
        </Button>
      </div>

      {error ? (
        <Card className="border-destructive/20">
          <CardContent className="py-4 text-sm text-destructive">{error}</CardContent>
        </Card>
      ) : null}

      {showNewForm ? (
        <Card>
          <CardHeader>
            <CardTitle>File a new challenge</CardTitle>
            <CardDescription>
              Select the transaction in question and describe why the activity should be reviewed.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <FieldGroup>
              <Field>
                <FieldLabel htmlFor="challenge-transaction">Transaction</FieldLabel>
                <FieldContent>
                  <Select
                    value={selectedTxnId ? String(selectedTxnId) : ''}
                    onValueChange={(value) => setSelectedTxnId(Number(value))}
                  >
                    <SelectTrigger id="challenge-transaction">
                      <SelectValue placeholder="Select a transaction" />
                    </SelectTrigger>
                    <SelectContent>
                      {transactions.map((transaction) => (
                        <SelectItem key={transaction.id} value={String(transaction.id)}>
                          {formatCurrency(transaction.amount)} · {transaction.description || 'No description'}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </FieldContent>
              </Field>

              <Field>
                <FieldLabel htmlFor="challenge-reason">Reason</FieldLabel>
                <FieldContent>
                  <Textarea
                    id="challenge-reason"
                    value={reason}
                    onChange={(event) => setReason(event.target.value)}
                    placeholder="Explain why this transaction should be challenged."
                    rows={4}
                  />
                </FieldContent>
              </Field>

              <Button
                type="button"
                onClick={() => void handleCreateChallenge()}
                disabled={trust.state !== 'verified' || !selectedTxnId || !reason.trim() || submitting}
              >
                {submitting ? 'Submitting…' : trust.state === 'verified' ? 'Submit challenge' : 'Trust required'}
              </Button>
            </FieldGroup>
          </CardContent>
        </Card>
      ) : null}

      {challenges.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center gap-3 py-12 text-center">
            <FileWarning className="size-8 text-muted-foreground" />
            <div className="space-y-1">
              <p className="font-medium text-foreground">No active challenges</p>
              <p className="text-sm text-muted-foreground">
                Open the form when a transaction needs an evidence-backed review trail.
              </p>
            </div>
          </CardContent>
        </Card>
      ) : (
        <div className="flex flex-col gap-4">
          {challenges.map((challenge) => {
            const transaction = transactionMap.get(challenge.transaction_id);
            const badge = getChallengeBadge(challenge.status);

            return (
              <Card key={challenge.id} size="sm">
                <CardHeader className="gap-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="space-y-2">
                      <div className="flex flex-wrap items-center gap-2">
                        <Badge variant={badge.variant}>{badge.label}</Badge>
                        <CardTitle className="text-base font-medium">Challenge #{challenge.id}</CardTitle>
                      </div>
                      <CardDescription>
                        Opened {new Date(challenge.created_at).toLocaleString()}
                      </CardDescription>
                    </div>
                    {challenge.status === 'pending' && canResolveChallenges ? (
                      <Button type="button" variant="secondary" onClick={() => void handleResolve(challenge.id)}>
                        Resolve with evidence
                      </Button>
                    ) : null}
                  </div>
                </CardHeader>
                <CardContent className="space-y-4 pt-0">
                  {transaction ? (
                    <div className="rounded-3xl bg-secondary/60 px-4 py-3">
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <div className="space-y-1">
                          <div className="text-sm font-medium text-foreground">
                            {transaction.description || 'Transaction'}
                          </div>
                          <div className="text-sm text-muted-foreground">{transaction.vpa || 'Unknown VPA'}</div>
                        </div>
                        <div className="text-sm font-medium text-foreground">
                          {transaction.transaction_type === 'inflow' ? '+' : '-'}
                          {formatCurrency(transaction.amount)}
                        </div>
                      </div>
                    </div>
                  ) : null}

                  <p className="text-sm text-foreground">{challenge.reason}</p>

                  {challenge.evidence ? (
                    <div className="text-sm">
                      <span className="font-medium text-foreground">Evidence: </span>
                      <a className="text-primary underline-offset-4 hover:underline" href={challenge.evidence} target="_blank" rel="noreferrer">
                        {challenge.evidence}
                      </a>
                    </div>
                  ) : null}

                  {challenge.resolved_at ? (
                    <div className="inline-flex items-center gap-2 text-sm text-muted-foreground">
                      <CheckCircle2 className="size-4 text-primary" />
                      Resolved {new Date(challenge.resolved_at).toLocaleString()}
                    </div>
                  ) : challenge.status === 'pending' ? (
                    <div className="inline-flex items-center gap-2 text-sm text-muted-foreground">
                      <AlertTriangle className="size-4 text-primary" />
                      Awaiting evidence-backed resolution
                    </div>
                  ) : null}
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </PageLayout>
  );
}

export default function ChallengesPage() {
  return (
    <ProtectedRoute>
      <ChallengesContent />
    </ProtectedRoute>
  );
}
