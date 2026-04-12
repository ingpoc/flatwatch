'use client';

import { ArrowRight, ShieldCheck } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';

export default function Home() {
  return (
    <div className="premium-shell flex min-h-screen items-center justify-center px-6 py-20">
      <main className="flex w-full max-w-4xl flex-col items-center gap-10 text-center">
        <div className="space-y-4">
          <div className="text-xs font-semibold uppercase tracking-[0.2em] text-muted-foreground">
            Trust Consumer Surface
          </div>
          <h1 className="text-5xl font-semibold tracking-[-0.06em] text-foreground sm:text-6xl">
            FlatWatch
          </h1>
          <p className="text-lg text-muted-foreground">Society Cash Tracker</p>
          <p className="mx-auto max-w-2xl text-base text-muted-foreground sm:text-lg">
            Financial transparency for housing societies, grounded in AadhaarChain trust and evidence-first workflows.
          </p>
        </div>

        <Card className="w-full max-w-2xl">
          <CardContent className="flex flex-col items-center gap-6 py-10">
            <div className="flex size-14 items-center justify-center rounded-full bg-primary/10 text-primary">
              <ShieldCheck className="size-6" />
            </div>
            <div className="space-y-2">
              <p className="text-lg font-medium text-foreground">
                Move from transaction review to trust-backed disputes without changing context.
              </p>
              <p className="text-sm text-muted-foreground">
                The operational shell, evidence intake, and agent workflows now follow the shared Luma trust-consumer standard.
              </p>
            </div>
            <Button size="lg" onClick={() => { window.location.href = '/dashboard'; }}>
              Get Started
              <ArrowRight className="size-4" />
            </Button>
          </CardContent>
        </Card>

        <div className="inline-flex items-center gap-2 rounded-full border border-border bg-card px-4 py-2 text-sm text-muted-foreground shadow-sm">
          <span className="size-2 rounded-full bg-primary" />
          System initializing...
        </div>
      </main>
    </div>
  );
}
