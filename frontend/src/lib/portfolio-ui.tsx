'use client';

import {
  forwardRef,
  useState,
  type ButtonHTMLAttributes,
  type CSSProperties,
  type HTMLAttributes,
  type ReactNode,
  type TextareaHTMLAttributes,
} from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { clsx, type ClassValue } from 'clsx';
import { Menu, X } from 'lucide-react';
import { twMerge } from 'tailwind-merge';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export type StatusTone = 'neutral' | 'success' | 'warning' | 'error' | 'info';

export interface NavItem {
  href: string;
  label: string;
}

const toneClasses: Record<StatusTone, string> = {
  neutral: 'text-[var(--ui-text-secondary)] bg-[var(--ui-bg-subtle)] border-[var(--ui-border)]',
  success: 'text-[var(--ui-success)] bg-[rgba(19,121,91,0.12)] border-[rgba(19,121,91,0.14)]',
  warning: 'text-[var(--ui-warning)] bg-[rgba(180,83,9,0.12)] border-[rgba(180,83,9,0.14)]',
  error: 'text-[var(--ui-error)] bg-[rgba(194,65,12,0.12)] border-[rgba(194,65,12,0.14)]',
  info: 'text-[var(--ui-info)] bg-[rgba(29,78,216,0.12)] border-[rgba(29,78,216,0.14)]',
};

const buttonVariants = cva(
  'inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-[var(--ui-radius-pill)] text-sm font-semibold transition-all duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ui-ring)] disabled:pointer-events-none disabled:opacity-50',
  {
    variants: {
      variant: {
        default: 'bg-[var(--ui-primary)] text-white shadow-[0_10px_24px_rgba(234,106,42,0.24)] hover:bg-[var(--ui-primary-strong)]',
        secondary: 'border border-[var(--ui-border)] bg-white text-[var(--ui-text)] hover:bg-[rgba(255,255,255,0.7)]',
        ghost: 'bg-transparent text-[var(--ui-text)] hover:bg-[rgba(16,16,16,0.04)]',
        subtle: 'bg-[var(--ui-bg-subtle)] text-[var(--ui-text)] hover:bg-[#e6e1d8]',
        danger: 'bg-[var(--ui-error)] text-white shadow-[0_10px_24px_rgba(194,65,12,0.24)]',
      },
      size: {
        default: 'h-11 px-5',
        sm: 'h-9 px-4 text-xs',
        lg: 'h-12 px-6 text-base',
        icon: 'h-11 w-11',
      },
      fullWidth: {
        true: 'w-full',
        false: '',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
      fullWidth: false,
    },
  }
);

export interface ButtonProps
  extends ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  children?: ReactNode;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, fullWidth, ...props }, ref) => (
    <button ref={ref} className={cn(buttonVariants({ variant, size, fullWidth }), className)} {...props} />
  )
);
Button.displayName = 'Button';

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaHTMLAttributes<HTMLTextAreaElement>>(
  ({ className, ...props }, ref) => (
    <textarea
      ref={ref}
      className={cn(
        'flex min-h-[120px] w-full rounded-[var(--ui-radius-md)] border border-[var(--ui-border)] bg-white px-4 py-3 text-sm font-medium text-[var(--ui-text)] shadow-[var(--ui-shadow-sm)] outline-none transition-all duration-150 placeholder:text-[var(--ui-text-muted)] focus:border-[var(--ui-primary)] focus:ring-2 focus:ring-[var(--ui-ring)] disabled:cursor-not-allowed disabled:opacity-50',
        className
      )}
      {...props}
    />
  )
);
Textarea.displayName = 'Textarea';

export const Card = forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement>>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn(
      'surface-card rounded-[var(--ui-radius-lg)] border border-[var(--ui-border)] bg-[rgba(255,255,255,0.88)] p-6 backdrop-blur-sm',
      className
    )}
    {...props}
  />
));
Card.displayName = 'Card';

export function Badge({
  tone = 'neutral',
  className,
  children,
}: {
  tone?: StatusTone;
  className?: string;
  children: ReactNode;
}) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-[var(--ui-radius-pill)] border px-3 py-1 text-[11px] font-bold uppercase tracking-[0.12em]',
        toneClasses[tone],
        className
      )}
    >
      {children}
    </span>
  );
}

export function Alert({
  title,
  description,
  tone = 'info',
  action,
  className,
}: {
  title: ReactNode;
  description?: ReactNode;
  tone?: StatusTone;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <Card className={cn('rounded-[var(--ui-radius-lg)] border p-5', toneClasses[tone], className)}>
      <div className="space-y-2">
        <div className="text-sm font-bold uppercase tracking-[0.14em]">{title}</div>
        {description ? <div className="text-sm leading-6">{description}</div> : null}
        {action ? <div className="pt-2">{action}</div> : null}
      </div>
    </Card>
  );
}

export function TrustBanner({
  title,
  description,
  action,
  tone = 'warning',
}: {
  title: ReactNode;
  description: ReactNode;
  action?: ReactNode;
  tone?: StatusTone;
}) {
  return <Alert title={title} description={description} action={action} tone={tone} className="rounded-[var(--ui-radius-lg)]" />;
}

export function PageLayout({
  children,
  title,
  subtitle,
  showHeader = false,
}: {
  children: ReactNode;
  title?: string;
  subtitle?: string;
  showHeader?: boolean;
}) {
  return (
    <div className="mx-auto w-full max-w-[1280px] px-4 py-6 sm:px-6 lg:px-8">
      {(showHeader || title || subtitle) ? (
        <div className="mb-6 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div className="space-y-2">
            {title ? <h1 className="text-[clamp(2rem,4vw,3rem)] font-bold tracking-[-0.04em] text-[var(--ui-text)]">{title}</h1> : null}
            {subtitle ? <p className="max-w-3xl text-sm text-[var(--ui-text-secondary)] sm:text-base">{subtitle}</p> : null}
          </div>
        </div>
      ) : null}
      {children}
    </div>
  );
}

export function StatCard({
  label,
  value,
  hint,
  tone = 'neutral',
}: {
  label: string;
  value: ReactNode;
  hint?: ReactNode;
  tone?: StatusTone;
}) {
  return (
    <Card className="rounded-[var(--ui-radius-lg)] p-5">
      <div className="text-xs font-bold uppercase tracking-[0.12em] text-[var(--ui-text-muted)]">{label}</div>
      <div className="mt-4 text-3xl font-bold tracking-[-0.04em] text-[var(--ui-text)]">{value}</div>
      {hint ? <div className={cn('mt-3 text-sm font-medium', toneClasses[tone].split(' ')[0])}>{hint}</div> : null}
    </Card>
  );
}

export function ChatLayout({
  title,
  children,
  footer,
  actions,
  height = '640px',
}: {
  title: string;
  children: ReactNode;
  footer?: ReactNode;
  actions?: ReactNode;
  height?: CSSProperties['height'];
}) {
  return (
    <Card className="overflow-hidden p-0">
      <div className="flex items-center justify-between border-b border-[var(--ui-border)] px-5 py-4">
        <div>
          <div className="text-xs font-bold uppercase tracking-[0.18em] text-[var(--ui-text-muted)]">Assistant</div>
          <div className="text-lg font-bold tracking-[-0.03em] text-[var(--ui-text)]">{title}</div>
        </div>
        {actions}
      </div>
      <div className="flex flex-col" style={{ height }}>
        <div className="hide-scrollbar flex-1 overflow-y-auto px-5 py-4">{children}</div>
        {footer ? <div className="border-t border-[var(--ui-border)] bg-[rgba(255,255,255,0.7)] px-5 py-4">{footer}</div> : null}
      </div>
    </Card>
  );
}

export function AppShell({
  brand,
  navItems,
  activePath,
  renderLink,
  actions,
  headerSearch,
  children,
}: {
  brand: {
    name: string;
    href: string;
    tagline?: string;
  };
  navItems: NavItem[];
  activePath?: string;
  renderLink: (item: NavItem, className: string, isActive: boolean, onNavigate?: () => void) => ReactNode;
  actions?: ReactNode;
  headerSearch?: ReactNode;
  children: ReactNode;
}) {
  const [mobileOpen, setMobileOpen] = useState(false);

  const desktopLinkClass = (isActive: boolean) =>
    cn(
      'rounded-[var(--ui-radius-pill)] px-4 py-2 text-sm font-semibold transition-all duration-150',
      isActive
        ? 'bg-[rgba(234,106,42,0.12)] text-[var(--ui-primary-strong)]'
        : 'text-[var(--ui-text-secondary)] hover:bg-[rgba(16,16,16,0.04)] hover:text-[var(--ui-text)]'
    );

  return (
    <div className="premium-shell min-h-screen">
      <header className="sticky top-0 z-40 border-b border-[var(--ui-border)] bg-[rgba(246,244,239,0.82)] backdrop-blur-xl">
        <div className="mx-auto flex max-w-[1440px] items-center gap-3 px-4 py-4 sm:px-6 lg:px-8">
          <div className="min-w-0">
            <div className="text-xs font-bold uppercase tracking-[0.18em] text-[var(--ui-text-muted)]">Portfolio</div>
            {renderLink(
              { href: brand.href, label: brand.name },
              'block text-[1.5rem] font-bold tracking-[-0.05em] text-[var(--ui-text)]',
              activePath === brand.href
            )}
            {brand.tagline ? <div className="mt-1 hidden text-sm text-[var(--ui-text-secondary)] sm:block">{brand.tagline}</div> : null}
          </div>
          <nav className="ml-4 hidden flex-1 items-center gap-1 lg:flex">
            {navItems.map((item) => renderLink(item, desktopLinkClass(activePath === item.href), activePath === item.href))}
          </nav>
          <div className="ml-auto hidden items-center gap-3 lg:flex">
            {headerSearch}
            {actions}
          </div>
          <div className="ml-auto lg:hidden">
            <Button variant="secondary" size="icon" type="button" onClick={() => setMobileOpen((open) => !open)} aria-label="Open navigation">
              {mobileOpen ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
            </Button>
          </div>
        </div>
        {mobileOpen ? (
          <div className="border-t border-[var(--ui-border)] bg-[rgba(246,244,239,0.96)] px-4 py-4 lg:hidden">
            <div className="space-y-2">
              {navItems.map((item) =>
                renderLink(item, desktopLinkClass(activePath === item.href), activePath === item.href, () => setMobileOpen(false))
              )}
            </div>
            {actions ? <div className="mt-4 flex flex-wrap items-center gap-3">{actions}</div> : null}
          </div>
        ) : null}
      </header>
      {children}
    </div>
  );
}
