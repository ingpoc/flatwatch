'use client';

import { useState, type CSSProperties, type ReactNode } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useWallet } from '@solana/wallet-adapter-react';
import { WalletMultiButton } from '@solana/wallet-adapter-react-ui';
import { Menu, ShieldAlert, ShieldCheck, ShieldX } from 'lucide-react';
import { useTrustState } from '@/lib/useTrustState';
import { cn } from '@/lib/utils';
import { Button, buttonVariants } from '@/components/ui/button';
import { ButtonGroup, ButtonGroupText } from '@/components/ui/button-group';
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from '@/components/ui/sheet';

const NAV_ITEMS = [
  { href: '/dashboard', label: 'Dashboard' },
  { href: '/transactions', label: 'Transactions' },
  { href: '/receipts', label: 'Receipts' },
  { href: '/challenges', label: 'Challenges' },
  { href: '/chat', label: 'Chat' },
] as const;

const WALLET_BUTTON_STYLE: CSSProperties = {
  backgroundColor: 'var(--primary)',
  color: 'var(--primary-foreground)',
  borderRadius: '999px',
  boxShadow: 'var(--wallet-shadow)',
  height: '40px',
  padding: '0 16px',
  fontSize: '0.875rem',
  fontWeight: 600,
};

type TrustState =
  | 'no_identity'
  | 'identity_present_unverified'
  | 'verified'
  | 'manual_review'
  | 'revoked_or_blocked';

function getActivePath(pathname: string) {
  if (pathname.startsWith('/transactions')) {
    return '/transactions';
  }
  if (pathname.startsWith('/receipts')) {
    return '/receipts';
  }
  if (pathname.startsWith('/challenges')) {
    return '/challenges';
  }
  if (pathname.startsWith('/chat')) {
    return '/chat';
  }
  return '/dashboard';
}

function getTrustMeta(state: TrustState, loading: boolean) {
  if (loading) {
    return {
      label: 'Syncing',
      detail: 'Refreshing AadhaarChain trust state.',
      icon: ShieldAlert,
      toneClass: 'bg-secondary text-secondary-foreground',
    };
  }

  switch (state) {
    case 'verified':
      return {
        label: 'Verified',
        detail: 'AadhaarChain verification is active for trust-gated actions.',
        icon: ShieldCheck,
        toneClass: 'bg-primary/12 text-primary',
      };
    case 'identity_present_unverified':
      return {
        label: 'Identity',
        detail: 'An identity exists, but verification is incomplete.',
        icon: ShieldAlert,
        toneClass: 'bg-accent text-accent-foreground',
      };
    case 'manual_review':
      return {
        label: 'Review',
        detail: 'Verification is pending manual review.',
        icon: ShieldAlert,
        toneClass: 'bg-accent text-accent-foreground',
      };
    case 'revoked_or_blocked':
      return {
        label: 'Blocked',
        detail: 'AadhaarChain is blocking elevated trust actions.',
        icon: ShieldX,
        toneClass: 'bg-destructive/12 text-destructive',
      };
    default:
      return {
        label: 'No ID',
        detail: 'Connect the AadhaarChain identity wallet to unlock trust-gated flows.',
        icon: ShieldAlert,
        toneClass: 'bg-secondary text-secondary-foreground',
      };
  }
}

function DesktopTrustRail({
  loading,
  state,
  expanded,
  onToggle,
}: {
  loading: boolean;
  state: TrustState;
  expanded: boolean;
  onToggle: () => void;
}) {
  const meta = getTrustMeta(state, loading);
  const Icon = meta.icon;

  if (!expanded) {
    return (
      <Button
        type="button"
        variant="outline"
        size="icon-sm"
        className="rounded-full shadow-sm"
        onClick={onToggle}
        aria-label={`Trust status: ${meta.label}`}
      >
        <Icon className="size-4" />
      </Button>
    );
  }

  return (
    <ButtonGroup className="shadow-sm">
      <Button
        type="button"
        variant="secondary"
        size="icon-sm"
        className={cn('rounded-full border-0', meta.toneClass)}
        onClick={onToggle}
        aria-label="Collapse trust status"
      >
        <Icon className="size-4" />
      </Button>
      <ButtonGroupText className="rounded-full border-0 bg-secondary/90 pr-4 text-foreground">
        <span className="font-medium">Trust {meta.label}</span>
      </ButtonGroupText>
    </ButtonGroup>
  );
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
  const activePath = getActivePath(pathname);
  const { publicKey } = useWallet();
  const trust = useTrustState(publicKey?.toBase58() ?? null);
  const [trustExpanded, setTrustExpanded] = useState(false);

  return (
    <div className="premium-shell min-h-screen">
      <header className="sticky top-0 z-40 border-b border-border/70 bg-background/80 backdrop-blur-xl">
        <div className="mx-auto flex max-w-[1500px] items-center gap-3 px-4 py-4 sm:px-6 lg:px-8">
          <div className="min-w-0 shrink-0">
            <div className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">
              Trust Consumer
            </div>
            <Link href="/dashboard" className="block text-[1.5rem] font-semibold tracking-[-0.05em] text-foreground">
              FlatWatch
            </Link>
            <p className="mt-1 hidden text-sm text-muted-foreground sm:block">
              Transparency, evidence, and challenge workflows for housing societies.
            </p>
          </div>

          <nav className="hidden min-w-0 flex-1 items-center justify-center gap-1 lg:flex">
            {NAV_ITEMS.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  buttonVariants({
                    variant: activePath === item.href ? 'secondary' : 'ghost',
                    size: 'sm',
                  }),
                  'rounded-full px-4',
                )}
                aria-current={activePath === item.href ? 'page' : undefined}
              >
                {item.label}
              </Link>
            ))}
          </nav>

          <div className="ml-auto hidden items-center gap-3 lg:flex">
            <DesktopTrustRail
              loading={trust.loading}
              state={trust.state}
              expanded={trustExpanded}
              onToggle={() => setTrustExpanded((current) => !current)}
            />
            <WalletMultiButton style={WALLET_BUTTON_STYLE} />
          </div>

          <div className="ml-auto lg:hidden">
            <Sheet>
              <SheetTrigger asChild>
                <Button type="button" variant="outline" size="icon-sm" className="rounded-full shadow-sm" aria-label="Open navigation">
                  <Menu className="size-4" />
                </Button>
              </SheetTrigger>
              <SheetContent side="right" className="w-[min(88vw,24rem)]">
                <SheetHeader>
                  <SheetTitle>FlatWatch</SheetTitle>
                  <SheetDescription>
                    Trust-aware transaction, receipt, and challenge workflows.
                  </SheetDescription>
                </SheetHeader>
                <div className="flex flex-col gap-3 px-6 pb-6">
                  {NAV_ITEMS.map((item) => (
                    <Link
                      key={item.href}
                      href={item.href}
                      className={cn(
                        buttonVariants({
                          variant: activePath === item.href ? 'secondary' : 'ghost',
                        }),
                        'justify-start rounded-full',
                      )}
                      aria-current={activePath === item.href ? 'page' : undefined}
                    >
                      {item.label}
                    </Link>
                  ))}
                  <div className="rounded-3xl border border-border bg-card px-4 py-3">
                    <div className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                      Trust
                    </div>
                    <div className="mt-2 text-sm font-medium text-foreground">
                      {getTrustMeta(trust.state, trust.loading).detail}
                    </div>
                  </div>
                  <WalletMultiButton style={WALLET_BUTTON_STYLE} />
                </div>
              </SheetContent>
            </Sheet>
          </div>
        </div>
      </header>

      <main className="mx-auto flex max-w-[1500px] flex-col gap-8 px-4 py-8 sm:px-6 lg:px-8">
        <section className="space-y-2">
          <div className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">
            Operational view
          </div>
          <div className="space-y-2">
            <h1 className="text-3xl font-semibold tracking-[-0.05em] text-foreground sm:text-4xl">
              {title}
            </h1>
            {description ? (
              <p className="max-w-3xl text-sm text-muted-foreground sm:text-base">{description}</p>
            ) : null}
          </div>
        </section>

        {children}
      </main>
    </div>
  );
}
