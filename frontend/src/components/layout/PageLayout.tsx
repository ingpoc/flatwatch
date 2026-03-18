'use client';

import type { ReactNode } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { AppShell, Badge, PageLayout as PortfolioPageLayout, type NavItem } from '@/lib/portfolio-ui';
import { WalletMultiButton } from '@solana/wallet-adapter-react-ui';
import { useWallet } from '@solana/wallet-adapter-react';
import { useTrustState } from '@/lib/useTrustState';

const NAV_ITEMS: NavItem[] = [
  { href: '/dashboard', label: 'Dashboard' },
  { href: '/transactions', label: 'Transactions' },
  { href: '/receipts', label: 'Receipts' },
  { href: '/challenges', label: 'Challenges' },
  { href: '/chat', label: 'AI Chat' },
];

const WALLET_BUTTON_STYLE = {
  backgroundColor: 'var(--ui-primary)',
  borderRadius: '999px',
  boxShadow: '0 10px 24px rgba(234,106,42,0.24)',
  height: '44px',
  padding: '0 18px',
  fontSize: '0.875rem',
  fontWeight: 700,
};

function getActivePath(pathname: string): string {
  if (pathname.startsWith('/receipts')) {
    return '/receipts';
  }
  if (pathname.startsWith('/challenges')) {
    return '/challenges';
  }
  if (pathname.startsWith('/chat')) {
    return '/chat';
  }
  if (pathname.startsWith('/transactions')) {
    return '/transactions';
  }
  return '/dashboard';
}

function TrustStatusChip({
  loading,
  state,
}: {
  loading: boolean;
  state: 'no_identity' | 'identity_present_unverified' | 'verified' | 'manual_review' | 'revoked_or_blocked';
}) {
  if (loading) {
    return <Badge tone="neutral">Syncing trust</Badge>;
  }

  if (state === 'verified') {
    return <Badge tone="success">AadhaarChain verified</Badge>;
  }

  if (state === 'identity_present_unverified') {
    return <Badge tone="warning">Identity present</Badge>;
  }

  if (state === 'manual_review') {
    return <Badge tone="warning">Manual review</Badge>;
  }

  if (state === 'revoked_or_blocked') {
    return <Badge tone="error">Trust blocked</Badge>;
  }

  return <Badge tone="neutral">No identity</Badge>;
}

export function PageLayout({
  title,
  description,
  children,
}: {
  title: string;
  description?: string;
  children: ReactNode;
}) {
  const pathname = usePathname();
  const { publicKey } = useWallet();
  const trust = useTrustState(publicKey?.toBase58() ?? null);

  return (
    <AppShell
      brand={{
        name: 'FlatWatch',
        href: '/dashboard',
        tagline: 'Transparency, evidence, and challenge workflows.',
      }}
      navItems={NAV_ITEMS}
      activePath={getActivePath(pathname)}
      renderLink={(item, className, isActive, onNavigate) => (
        <Link
          key={item.href}
          href={item.href}
          className={className}
          aria-current={isActive ? 'page' : undefined}
          onClick={onNavigate}
        >
          {item.label}
        </Link>
      )}
      actions={
        <>
          <TrustStatusChip loading={trust.loading} state={trust.state} />
          <WalletMultiButton style={WALLET_BUTTON_STYLE} />
        </>
      }
    >
      <PortfolioPageLayout title={title} subtitle={description} showHeader>
        {children}
      </PortfolioPageLayout>
    </AppShell>
  );
}
