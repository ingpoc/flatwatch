'use client';

import type { ReactNode } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Spinner } from '@/components/ui/spinner';
import { useAuth } from './auth';

interface ProtectedRouteProps {
  children: ReactNode;
}

function CenteredState({
  title,
  description,
  action,
}: {
  title: string;
  description: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="premium-shell flex min-h-screen items-center justify-center px-4 py-10">
      <Card className="w-full max-w-lg">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl font-semibold tracking-[-0.04em]">{title}</CardTitle>
          <CardDescription>{description}</CardDescription>
        </CardHeader>
        {action ? <CardContent className="flex justify-center pt-0">{action}</CardContent> : null}
      </Card>
    </div>
  );
}

export function ProtectedRoute({ children }: ProtectedRouteProps) {
  const { user, loading, login, error } = useAuth();

  if (loading) {
    return (
      <CenteredState
        title="Verifying session"
        description={
          <span className="inline-flex items-center justify-center gap-2">
            <Spinner className="size-4" />
            Checking the local FlatWatch operator session.
          </span>
        }
      />
    );
  }

  if (!user) {
    return (
      <CenteredState
        title="Sign in required"
        description={
          <span className="space-y-2 text-center">
            <span className="block">Use the FlatWatch demo operator account to access the dashboard.</span>
            {error ? <span className="block text-destructive">{error}</span> : null}
          </span>
        }
        action={
          <Button type="button" onClick={() => void login()}>
            Sign in
          </Button>
        }
      />
    );
  }

  return <>{children}</>;
}
