// Challenge Mode - Dispute suspicious transactions
'use client';

import { useEffect, useState } from 'react';
import { PageLayout } from '@/components/layout/PageLayout';
import { TrustPanel } from '@/components/trust/TrustPanel';
import { ProtectedRoute } from '@/lib/ProtectedRoute';
import { useAuth } from '@/lib/auth';
import { challengesApi, transactionsApi } from '@/lib/api';
import type { Challenge, Transaction } from '@/lib/api';
import { useTrustState } from '@/lib/useTrustState';
import { useWallet } from '@solana/wallet-adapter-react';

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

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setError(null);
      const [challengesData, transactionsData] = await Promise.all([
        challengesApi.list(),
        transactionsApi.list({ limit: 50 }),
      ]);
      setChallenges(Array.isArray(challengesData) ? challengesData : []);
      setTransactions(Array.isArray(transactionsData) ? transactionsData : []);
    } catch {
      setError('Failed to load data');
      setChallenges([]);
      setTransactions([]);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateChallenge = async () => {
    if (!selectedTxnId || !reason.trim() || submitting) return;
    if (trust.state !== 'verified') {
      setError(trust.reason || 'Complete AadhaarChain verification before filing a challenge.');
      return;
    }

    setSubmitting(true);
    try {
      await challengesApi.create(selectedTxnId, reason);
      setShowNewForm(false);
      setSelectedTxnId(null);
      setReason('');
      await loadData();
    } catch {
      setError('Failed to create challenge');
    } finally {
      setSubmitting(false);
    }
  };

  const handleResolve = async (challengeId: number) => {
    if (trust.state !== 'verified') {
      setError(trust.reason || 'Complete AadhaarChain verification before resolving a challenge.');
      return;
    }

    const evidence = prompt('Enter evidence URL:');
    if (!evidence) return;

    try {
      await challengesApi.resolve(challengeId, evidence);
      await loadData();
    } catch {
      setError(canResolveChallenges ? 'Failed to resolve challenge' : 'Only admins can resolve challenges.');
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'pending': return 'rgb(255,152,0)';
      case 'resolved': return 'rgb(76,175,80)';
      case 'rejected': return 'rgb(244,67,54)';
      default: return 'rgb(158,158,158)';
    }
  };

  const getTransactionById = (id: number) => {
    return transactions.find(t => t.id === id);
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', minHeight: '100vh', alignItems: 'center', justifyContent: 'center', backgroundColor: 'white' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ width: '12px', height: '12px', borderRadius: '50%', backgroundColor: 'rgb(255,97,26)', animation: 'pulse 1s infinite' }} />
          <span style={{ color: '#999' }}>Loading...</span>
        </div>
      </div>
    );
  }

  return (
    <PageLayout title="Challenge Mode" description="Dispute suspicious transactions">
      <TrustPanel
        state={trust.state}
        loading={trust.loading}
        error={trust.error}
        reason={trust.reason}
        walletConnected={Boolean(publicKey)}
        actionLabel={publicKey ? 'Resolve challenge trust in AadhaarChain' : null}
      />

      {/* Error message */}
      {error && (
        <div style={{ marginBottom: '24px', borderRadius: '16px', backgroundColor: 'rgb(255,243,224)', padding: '16px', color: 'rgb(255,97,26)' }}>
          {error}
        </div>
      )}

      {/* New Challenge Button */}
      <div style={{ display: 'flex', justifyContent: 'center', marginBottom: '32px' }}>
        <button
          onClick={() => setShowNewForm(!showNewForm)}
          disabled={trust.state !== 'verified'}
          style={{
            height: '48px',
            borderRadius: '999px',
            backgroundColor: trust.state === 'verified' ? 'rgb(255,97,26)' : 'rgb(238,238,238)',
            padding: '0 24px',
            fontSize: '14px',
            fontWeight: 500,
            color: trust.state === 'verified' ? 'white' : '#999',
            border: 'none',
            boxShadow: trust.state === 'verified' ? '0 2px 8px rgba(255,97,26,0.3)' : 'none',
            transition: 'all 0.2s',
            cursor: trust.state === 'verified' ? 'pointer' : 'not-allowed'
          }}
          onMouseEnter={(e) => {
            if (trust.state === 'verified') {
              e.currentTarget.style.boxShadow = '0 4px 12px rgba(255,97,26,0.4)';
            }
          }}
          onMouseLeave={(e) => {
            if (trust.state === 'verified') {
              e.currentTarget.style.boxShadow = '0 2px 8px rgba(255,97,26,0.3)';
            }
          }}
        >
          {trust.state === 'verified' ? (showNewForm ? 'Cancel' : 'New Challenge') : 'Verified trust required'}
        </button>
      </div>

      {/* New Challenge Form */}
      {showNewForm && (
        <div style={{ width: '100%', borderRadius: '24px', backgroundColor: 'white', padding: '24px', boxShadow: '0 4px 16px rgba(0,0,0,0.06)' }}>
          <h2 style={{ fontSize: '20px', fontWeight: 500, color: '#333', marginBottom: '24px' }}>Create New Challenge</h2>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '14px', fontWeight: 500, color: '#333', marginBottom: '8px' }}>Transaction</label>
              <select
                value={selectedTxnId || ''}
                onChange={e => setSelectedTxnId(e.target.value ? Number(e.target.value) : null)}
                style={{
                  width: '100%',
                  borderRadius: '999px',
                  border: '1px solid rgb(238,238,238)',
                  backgroundColor: 'rgb(249,249,249)',
                  padding: '12px 16px',
                  fontSize: '14px',
                  color: '#333',
                  outline: 'none',
                  transition: 'all 0.2s'
                }}
                onFocus={(e) => { e.currentTarget.style.borderColor = 'rgb(255,97,26)'; }}
                onBlur={(e) => { e.currentTarget.style.borderColor = 'rgb(238,238,238)'; }}
              >
                <option value="">Select a transaction</option>
                {transactions.map(txn => (
                  <option key={txn.id} value={txn.id}>
                    {txn.description || 'No description'} - ₹{txn.amount} ({txn.transaction_type})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '14px', fontWeight: 500, color: '#333', marginBottom: '8px' }}>Reason for Challenge</label>
              <textarea
                value={reason}
                onChange={e => setReason(e.target.value)}
                placeholder="Explain why you're disputing this transaction..."
                rows={3}
                style={{
                  width: '100%',
                  borderRadius: '16px',
                  border: '1px solid rgb(238,238,238)',
                  backgroundColor: 'rgb(249,249,249)',
                  padding: '12px 16px',
                  fontSize: '14px',
                  color: '#333',
                  outline: 'none',
                  transition: 'all 0.2s',
                  resize: 'vertical',
                  fontFamily: 'inherit'
                }}
                onFocus={(e) => { e.currentTarget.style.borderColor = 'rgb(255,97,26)'; }}
                onBlur={(e) => { e.currentTarget.style.borderColor = 'rgb(238,238,238)'; }}
              />
            </div>

            <button
              onClick={handleCreateChallenge}
              disabled={trust.state !== 'verified' || !selectedTxnId || !reason.trim() || submitting}
              style={{
                width: '100%',
                height: '48px',
                borderRadius: '999px',
                fontSize: '14px',
                fontWeight: 500,
                color: trust.state === 'verified' && selectedTxnId && reason.trim() && !submitting ? 'white' : '#999',
                border: 'none',
                backgroundColor: (trust.state === 'verified' && selectedTxnId && reason.trim() && !submitting) ? 'rgb(255,97,26)' : 'rgb(238,238,238)',
                boxShadow: (trust.state === 'verified' && selectedTxnId && reason.trim() && !submitting) ? '0 2px 8px rgba(255,97,26,0.3)' : 'none',
                cursor: (trust.state === 'verified' && selectedTxnId && reason.trim() && !submitting) ? 'pointer' : 'not-allowed',
                transition: 'all 0.2s'
              }}
              onMouseEnter={(e) => {
                if (trust.state === 'verified' && selectedTxnId && reason.trim() && !submitting) {
                  e.currentTarget.style.boxShadow = '0 4px 12px rgba(255,97,26,0.4)';
                }
              }}
              onMouseLeave={(e) => {
                if (trust.state === 'verified' && selectedTxnId && reason.trim() && !submitting) {
                  e.currentTarget.style.boxShadow = '0 2px 8px rgba(255,97,26,0.3)';
                }
              }}
            >
              {trust.state !== 'verified'
                ? 'Verified trust required'
                : submitting
                  ? 'Submitting...'
                  : 'Submit Challenge'}
            </button>
          </div>
        </div>
      )}

      {/* Challenges List */}
      <div>
        <h2 style={{ fontSize: '20px', fontWeight: 500, color: '#333', marginBottom: '16px' }}>
          Challenges ({challenges.length})
        </h2>

        {challenges.length === 0 ? (
          <div style={{ marginTop: '24px', textAlign: 'center', color: '#999' }}>No challenges yet</div>
        ) : (
          <div style={{ marginTop: '16px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {challenges.map((challenge) => {
              const txn = getTransactionById(challenge.transaction_id);
              const isPending = challenge.status === 'pending';
              const createdDate = new Date(challenge.created_at);
              const timeDiff = Date.now() - createdDate.getTime();
              const hoursRemaining = 48 - Math.floor(timeDiff / (1000 * 60 * 60));

              return (
                <div
                  key={challenge.id}
                  style={{
                    borderRadius: '16px',
                    backgroundColor: 'white',
                    padding: '20px',
                    boxShadow: '0 4px 16px rgba(0,0,0,0.06)',
                    transition: 'all 0.2s'
                  }}
                  onMouseEnter={(e) => { e.currentTarget.style.boxShadow = '0 8px 24px rgba(0,0,0,0.1)'; }}
                  onMouseLeave={(e) => { e.currentTarget.style.boxShadow = '0 4px 16px rgba(0,0,0,0.06)'; }}
                >
                  <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '16px' }}>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap', marginBottom: '8px' }}>
                        <h3 style={{ fontWeight: 500, color: '#333' }}>Challenge #{challenge.id}</h3>
                        <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: getStatusColor(challenge.status), flexShrink: 0 }} />
                        <span style={{ fontSize: '14px', color: '#999' }}>{challenge.status}</span>
                      </div>

                      {txn && (
                        <div style={{ marginTop: '12px', borderRadius: '16px', backgroundColor: 'rgb(249,249,249)', padding: '12px' }}>
                          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '16px' }}>
                            <div style={{ minWidth: 0, flex: 1 }}>
                              <p style={{ fontSize: '14px', fontWeight: 500, color: '#333', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                {txn.description || 'No description'}
                              </p>
                              <p style={{ marginTop: '4px', fontSize: '14px', color: '#999', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                {txn.vpa || 'Unknown VPA'}
                              </p>
                            </div>
                            <div style={{ textAlign: 'right', flexShrink: 0 }}>
                              <p style={{ fontSize: '16px', fontWeight: 600, color: '#333' }}>
                                {txn.transaction_type === 'inflow' ? '+' : '-'}₹{txn.amount}
                              </p>
                              <p style={{ fontSize: '12px', color: '#999' }}>
                                {new Date(txn.timestamp).toLocaleDateString()}
                              </p>
                            </div>
                          </div>
                        </div>
                      )}

                      <div style={{ marginTop: '12px' }}>
                        <p style={{ fontSize: '14px', color: '#333' }}>{challenge.reason}</p>
                      </div>

                      {isPending && hoursRemaining > 0 && (
                        <div style={{ marginTop: '12px', display: 'inline-flex', borderRadius: '999px', backgroundColor: 'rgb(255,243,224)', padding: '4px 12px' }}>
                          <p style={{ fontSize: '12px', color: 'rgb(255,97,26)', margin: 0 }}>
                            ⏰ {hoursRemaining}h remaining
                          </p>
                        </div>
                      )}

                      {challenge.resolved_at && (
                        <p style={{ marginTop: '12px', fontSize: '12px', color: '#999' }}>
                          Resolved: {new Date(challenge.resolved_at).toLocaleString()}
                        </p>
                      )}

                      {challenge.evidence && (
                        <div style={{ marginTop: '12px' }}>
                          <p style={{ fontSize: '12px', color: '#999', marginBottom: '4px' }}>Evidence:</p>
                          <a
                            href={challenge.evidence}
                            target="_blank"
                            rel="noopener"
                            style={{ fontSize: '12px', color: 'rgb(255,97,26)', textDecoration: 'none' }}
                            onMouseEnter={(e) => { e.currentTarget.style.textDecoration = 'underline'; }}
                            onMouseLeave={(e) => { e.currentTarget.style.textDecoration = 'none'; }}
                          >
                            {challenge.evidence}
                          </a>
                        </div>
                      )}
                    </div>

                    {isPending && canResolveChallenges && (
                      <button
                        onClick={() => handleResolve(challenge.id)}
                        disabled={trust.state !== 'verified'}
                        style={{
                          flexShrink: 0,
                          height: '40px',
                          borderRadius: '999px',
                          backgroundColor: trust.state === 'verified' ? 'rgb(76,175,80)' : 'rgb(238,238,238)',
                          padding: '0 16px',
                          fontSize: '14px',
                          fontWeight: 500,
                          color: trust.state === 'verified' ? 'white' : '#999',
                          border: 'none',
                          boxShadow: trust.state === 'verified' ? '0 2px 8px rgba(76,175,80,0.3)' : 'none',
                          transition: 'all 0.2s',
                          cursor: trust.state === 'verified' ? 'pointer' : 'not-allowed'
                        }}
                        onMouseEnter={(e) => {
                          if (trust.state === 'verified') {
                            e.currentTarget.style.boxShadow = '0 4px 12px rgba(76,175,80,0.4)';
                          }
                        }}
                        onMouseLeave={(e) => {
                          if (trust.state === 'verified') {
                            e.currentTarget.style.boxShadow = '0 2px 8px rgba(76,175,80,0.3)';
                          }
                        }}
                      >
                        {trust.state === 'verified' ? 'Resolve' : 'Trust required'}
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Footer status */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', borderRadius: '999px', backgroundColor: 'rgb(238,238,238)', padding: '12px 16px' }}>
        <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: 'rgb(76,175,80)' }} />
        <span style={{ fontSize: '14px', color: '#999' }}>System online • 48h resolution timer</span>
      </div>
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
