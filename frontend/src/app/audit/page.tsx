'use client';

import { useEffect, useState } from 'react';
import { PageLayout } from '@/components/layout/PageLayout';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Spinner } from '@/components/ui/spinner';
import { ProtectedRoute } from '@/lib/ProtectedRoute';
import { auditApi, type AuditLog, type AuditStats } from '@/lib/api';

function AuditContent() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [stats, setStats] = useState<AuditStats | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    Promise.all([auditApi.logs(), auditApi.stats()])
      .then(([nextLogs, nextStats]) => {
        if (!active) return;
        setLogs(nextLogs);
        setStats(nextStats);
        setError(null);
      })
      .catch((nextError: unknown) => {
        if (!active) return;
        setError(nextError instanceof Error ? nextError.message : 'Failed to load audit trail.');
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  return (
    <PageLayout title="Audit" description="Review sensitive actions, evidence access, and operator decisions.">
      {loading ? (
        <Card>
          <CardContent className="flex items-center gap-3 py-8 text-sm text-muted-foreground">
            <Spinner />
            Loading audit trail...
          </CardContent>
        </Card>
      ) : null}

      {error ? (
        <Card>
          <CardContent className="py-6 text-sm text-destructive">{error}</CardContent>
        </Card>
      ) : null}

      {!loading && !error ? (
        <>
          <section className="grid gap-3 md:grid-cols-3">
            <Card>
              <CardHeader>
                <CardTitle>Total events</CardTitle>
              </CardHeader>
              <CardContent className="text-2xl font-semibold">{stats?.total ?? 0}</CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Action types</CardTitle>
              </CardHeader>
              <CardContent className="text-2xl font-semibold">{Object.keys(stats?.by_action ?? {}).length}</CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Operators</CardTitle>
              </CardHeader>
              <CardContent className="text-2xl font-semibold">{Object.keys(stats?.by_user ?? {}).length}</CardContent>
            </Card>
          </section>

          <section className="overflow-hidden rounded-md border bg-card">
            <div className="grid grid-cols-[140px_120px_1fr] gap-3 border-b px-4 py-3 text-xs font-medium uppercase text-muted-foreground">
              <span>Action</span>
              <span>Target</span>
              <span>Details</span>
            </div>
            {logs.map((log) => (
              <div key={log.id} className="grid grid-cols-[140px_120px_1fr] gap-3 border-b px-4 py-3 text-sm last:border-b-0">
                <span className="font-medium">{log.action}</span>
                <span className="text-muted-foreground">{log.target_type ?? '-'}</span>
                <span>{log.details}</span>
              </div>
            ))}
          </section>
        </>
      ) : null}
    </PageLayout>
  );
}

export default function AuditPage() {
  return (
    <ProtectedRoute>
      <AuditContent />
    </ProtectedRoute>
  );
}
