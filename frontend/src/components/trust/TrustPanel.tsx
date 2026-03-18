'use client';

import { Button, TrustBanner } from '@/lib/portfolio-ui';
import type { PortfolioTrustState } from '@/lib/trust';

const IDENTITY_URL = process.env.NEXT_PUBLIC_IDENTITY_WEB_URL || 'http://127.0.0.1:3000';

const STATE_META: Record<
  PortfolioTrustState,
  { title: string; tone: 'neutral' | 'warning' | 'success' | 'error' }
> = {
  no_identity: {
    title: 'AadhaarChain trust: No identity',
    tone: 'neutral',
  },
  identity_present_unverified: {
    title: 'AadhaarChain trust: Unverified',
    tone: 'warning',
  },
  verified: {
    title: 'AadhaarChain trust: Verified',
    tone: 'success',
  },
  manual_review: {
    title: 'AadhaarChain trust: Manual review',
    tone: 'warning',
  },
  revoked_or_blocked: {
    title: 'AadhaarChain trust: Blocked',
    tone: 'error',
  },
};

export function TrustPanel({
  state,
  loading,
  error,
  reason,
  walletConnected = true,
  actionLabel = 'Open AadhaarChain',
}: {
  state: PortfolioTrustState;
  loading?: boolean;
  error?: string | null;
  reason?: string | null;
  walletConnected?: boolean;
  actionLabel?: string | null;
}) {
  if (loading) {
    return (
      <TrustBanner
        title="Loading AadhaarChain trust"
        description="Syncing the wallet-linked trust record before enabling evidence and challenge actions."
        tone="neutral"
      />
    );
  }

  const meta = STATE_META[state];
  const message =
    !walletConnected
      ? 'Connect the same Solflare wallet you use in AadhaarChain before using trust-gated evidence or challenge flows.'
      : error ||
        reason ||
        ({
          no_identity: 'Create an identity anchor in AadhaarChain before using auditable evidence or challenge flows.',
          identity_present_unverified: 'Complete AadhaarChain verification before uploading evidence or filing high-trust challenges.',
          manual_review: 'Verification is under manual review. Evidence-backed actions stay paused until review completes.',
          revoked_or_blocked: 'Trust state is blocked or revoked. Review AadhaarChain before attempting elevated transparency actions.',
          verified: 'Trust state is verified. Evidence and challenge actions can be attributed to a portable trust record.',
        }[state]);

  return (
    <TrustBanner
      title={meta.title}
      description={message}
      tone={meta.tone}
      action={
        actionLabel ? (
          <Button type="button" variant={state === 'verified' ? 'secondary' : 'default'} onClick={() => window.open(IDENTITY_URL, '_blank', 'noopener,noreferrer')}>
            {actionLabel}
          </Button>
        ) : undefined
      }
    />
  );
}
