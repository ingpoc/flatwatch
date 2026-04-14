'use client';

import { ShieldAlert, ShieldCheck, ShieldX } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { resolveIdentityWebUrl, type PortfolioTrustState } from '@/lib/trust';

const STATE_META: Record<
  PortfolioTrustState,
  {
    title: string;
    badge: 'secondary' | 'default' | 'destructive' | 'outline';
    icon: typeof ShieldAlert;
  }
> = {
  no_identity: {
    title: 'No identity',
    badge: 'outline',
    icon: ShieldAlert,
  },
  identity_present_unverified: {
    title: 'Identity present',
    badge: 'secondary',
    icon: ShieldAlert,
  },
  verified: {
    title: 'Verified',
    badge: 'default',
    icon: ShieldCheck,
  },
  manual_review: {
    title: 'Manual review',
    badge: 'secondary',
    icon: ShieldAlert,
  },
  revoked_or_blocked: {
    title: 'Blocked',
    badge: 'destructive',
    icon: ShieldX,
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
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Badge variant="outline">Syncing</Badge>
            <CardTitle>Loading AadhaarChain trust</CardTitle>
          </div>
          <CardDescription>
            Syncing the wallet-linked trust record before enabling evidence and challenge actions.
          </CardDescription>
        </CardHeader>
      </Card>
    );
  }

  const meta = STATE_META[state];
  const Icon = meta.icon;
  const message =
    !walletConnected
      ? 'Connect the same Solflare wallet you use in AadhaarChain before using trust-gated evidence or challenge flows.'
      : error ||
        reason ||
        ({
          no_identity: 'Create an identity anchor in AadhaarChain before using auditable evidence or challenge flows.',
          identity_present_unverified:
            'Complete AadhaarChain verification before uploading evidence or filing high-trust challenges.',
          manual_review:
            'Verification is under manual review. Evidence-backed actions stay paused until review completes.',
          revoked_or_blocked:
            'Trust state is blocked or revoked. Review AadhaarChain before attempting elevated transparency actions.',
          verified:
            'Trust state is verified. Evidence and challenge actions can be attributed to a portable trust record.',
        }[state]);

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex size-10 items-center justify-center rounded-2xl bg-secondary text-foreground">
            <Icon className="size-5" />
          </div>
          <div className="space-y-1">
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant={meta.badge}>AadhaarChain {meta.title}</Badge>
              <CardTitle>Trust status</CardTitle>
            </div>
            <CardDescription>{message}</CardDescription>
          </div>
        </div>
      </CardHeader>
      {actionLabel ? (
        <CardContent className="pt-0">
          <Button
            type="button"
            variant={state === 'verified' ? 'secondary' : 'default'}
            onClick={() => window.open(resolveIdentityWebUrl(), '_blank', 'noopener,noreferrer')}
          >
            {actionLabel}
          </Button>
        </CardContent>
      ) : null}
    </Card>
  );
}
