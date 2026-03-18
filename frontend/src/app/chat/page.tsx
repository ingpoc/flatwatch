'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { ArrowUp, Sparkles } from 'lucide-react';
import { useWallet } from '@solana/wallet-adapter-react';
import { Alert, Badge, Button, Card, ChatLayout, Textarea } from '@/lib/portfolio-ui';
import { PageLayout } from '@/components/layout/PageLayout';
import { ProtectedRoute } from '@/lib/ProtectedRoute';
import { agentApi, type AgentRuntimeSnapshot, type AgentSessionSummary, type UsageSnapshot } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import { useTrustState } from '@/lib/useTrustState';

const STORAGE_KEY = 'flatwatch-agent-session-id';

interface RenderMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
}

const DEFAULT_RUNTIME: AgentRuntimeSnapshot = {
  app_id: 'flatwatch',
  auth_mode: 'unavailable',
  model: 'claude-haiku-4-5-20251001',
  runtime_available: false,
  agent_access: false,
  trust_state: 'no_identity',
  trust_required_for_write: true,
  mode: 'blocked',
  usage: {
    requests_used: 0,
    requests_limit: 0,
    period_start: '',
    period_end: '',
    estimated_cost_usd: 0,
  },
  allowed_capabilities: [],
  blocked_reason: 'Authentication required.',
};

function getStoredSessionId() {
  if (typeof window === 'undefined') {
    return '';
  }
  return window.localStorage.getItem(STORAGE_KEY) ?? '';
}

function setStoredSessionId(sessionId: string) {
  if (typeof window !== 'undefined') {
    window.localStorage.setItem(STORAGE_KEY, sessionId);
  }
}

function UsageBadge({ usage }: { usage: UsageSnapshot }) {
  return (
    <Badge tone="info">
      {usage.requests_limit > 0
        ? `Usage ${usage.requests_used}/${usage.requests_limit}`
        : `${usage.requests_used} requests this period`}
    </Badge>
  );
}

function ChatContent() {
  const { user } = useAuth();
  const { publicKey } = useWallet();
  const walletAddress = publicKey?.toBase58() ?? null;
  const trust = useTrustState(walletAddress);
  const [messages, setMessages] = useState<RenderMessage[]>([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [streamingText, setStreamingText] = useState('');
  const [runtime, setRuntime] = useState<AgentRuntimeSnapshot>(DEFAULT_RUNTIME);
  const [runtimeLoading, setRuntimeLoading] = useState(false);
  const [session, setSession] = useState<AgentSessionSummary | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingText, sending]);

  useEffect(() => {
    if (!user) {
      setRuntime(DEFAULT_RUNTIME);
      setSession(null);
      return;
    }

    let cancelled = false;
    const run = async () => {
      try {
        setRuntimeLoading(true);
        setError(null);
        const next = await agentApi.getRuntime('flatwatch', walletAddress);
        if (!cancelled) {
          setRuntime(next);
        }
      } catch (err) {
        if (!cancelled) {
          setRuntime(DEFAULT_RUNTIME);
          setError(err instanceof Error ? err.message : 'Failed to load agent runtime.');
        }
      } finally {
        if (!cancelled) {
          setRuntimeLoading(false);
        }
      }
    };

    void run();

    return () => {
      cancelled = true;
    };
  }, [user, walletAddress]);

  const handleSend = async (nextInput = input) => {
    const message = nextInput.trim();
    if (!message || sending || !user || !runtime.agent_access) {
      return;
    }

    setError(null);
    setInput('');
    setSending(true);
    setMessages((current) => [...current, { role: 'user', content: message }]);

    try {
      const currentSession =
        session ??
        (await agentApi.createSession(
          'flatwatch',
          {
            task_type: 'trust_audit_assistant',
            context: { trust_state: trust.state, wallet_address: walletAddress },
            resume_session_id: getStoredSessionId() || undefined,
          },
          walletAddress,
        ));

      if (!session) {
        setSession(currentSession);
        setStoredSessionId(currentSession.session_id);
      }

      let finalResponse = '';
      let latestUsage = runtime.usage;

      await agentApi.streamMessage(
        'flatwatch',
        { session_id: currentSession.session_id, message },
        (event) => {
          if (event.type === 'assistant_delta') {
            setStreamingText((current) => current + event.content);
          }
          if (event.type === 'result') {
            finalResponse = event.content;
          }
          if (event.type === 'usage') {
            latestUsage = event.usage;
          }
          if (event.type === 'error') {
            setError(event.error);
          }
        },
        walletAddress,
      );

      if (finalResponse) {
        setMessages((current) => [...current, { role: 'assistant', content: finalResponse }]);
      }
      setRuntime((current) => ({
        ...current,
        usage: latestUsage,
      }));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send message.');
    } finally {
      setStreamingText('');
      setSending(false);
    }
  };

  const suggestedQueries = useMemo(
    () => [
      'Summarize this month’s inflows and outflows.',
      'Which receipts still need review?',
      'Show the latest resident challenges and likely next actions.',
      'Explain the by-law basis for disputed maintenance charges.',
    ],
    [],
  );

  return (
    <PageLayout title="Chat Guard" description="Claude-powered financial summaries, evidence review, and trust-aware guidance">
      <div className="space-y-4">
        <div className="flex flex-wrap gap-2">
          <Badge tone={runtime.runtime_available ? 'success' : 'warning'}>Runtime {runtime.auth_mode}</Badge>
          <Badge tone={trust.state === 'verified' ? 'success' : 'warning'}>
            {trust.state === 'verified' ? 'Verified write path enabled' : 'Read-only trust mode'}
          </Badge>
          <Badge tone="info">{runtime.model}</Badge>
          <UsageBadge usage={runtime.usage} />
        </div>

        {error ? <Alert title="Agent request failed" description={error} tone="error" /> : null}

        {!runtime.runtime_available && user ? (
          <Alert
            title="Claude runtime unavailable"
            description={runtime.blocked_reason ?? 'Configure supported Claude Agent SDK auth or use the local Claude CLI dev adapter on localhost.'}
            tone="warning"
          />
        ) : null}

        {runtime.agent_access && trust.state !== 'verified' ? (
          <Alert
            title="Trust verification limits write actions"
            description={trust.reason ?? 'You can use informational agent flows, but evidence-affecting actions stay read-only until AadhaarChain verification completes.'}
            tone="info"
          />
        ) : null}

        {messages.length === 0 ? (
          <Card className="space-y-6 p-8 text-center">
            <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-[rgba(234,106,42,0.12)] text-[var(--ui-primary)]">
              <Sparkles className="h-6 w-6" />
            </div>
            <div className="space-y-2">
              <h2 className="text-3xl font-bold tracking-[-0.04em] text-[var(--ui-text)]">How can I help you today?</h2>
              <p className="text-sm text-[var(--ui-text-secondary)]">
                Ask about receipts, transactions, anomalies, and challenge evidence.
              </p>
            </div>
            <div className="flex flex-wrap justify-center gap-3">
              {suggestedQueries.map((query) => (
                <Button
                  key={query}
                  type="button"
                  variant="secondary"
                  onClick={() => void handleSend(query)}
                  disabled={!runtime.agent_access || sending || runtimeLoading}
                >
                  {query}
                </Button>
              ))}
            </div>
          </Card>
        ) : null}

        <ChatLayout
          title="FlatWatch Agent"
          height="640px"
          actions={session ? <Badge tone="info">Session: {session.session_id.slice(0, 8)}</Badge> : null}
          footer={
            <div className="space-y-2">
              <div className="flex items-end gap-3">
                <Textarea
                  value={input}
                  onChange={(event) => setInput(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === 'Enter' && !event.shiftKey) {
                      event.preventDefault();
                      void handleSend();
                    }
                  }}
                  placeholder="Ask about transactions, receipts, challenges, or compliance..."
                  disabled={!runtime.agent_access || sending || runtimeLoading}
                  rows={2}
                  className="min-h-[88px] flex-1"
                />
                <Button
                  type="button"
                  size="icon"
                  onClick={() => void handleSend()}
                  disabled={!input.trim() || !runtime.agent_access || sending || runtimeLoading}
                  aria-label="Send message"
                >
                  <ArrowUp className="h-4 w-4" />
                </Button>
              </div>
              <p className="text-xs text-[var(--ui-text-secondary)]">
                Trust status controls elevated actions independently.
              </p>
            </div>
          }
        >
          <div className="space-y-4">
            {messages.length === 0 ? (
              <div className="flex h-full min-h-[280px] items-center justify-center">
                <Badge tone="neutral">Waiting for your first question</Badge>
              </div>
            ) : (
              messages.map((message, index) => (
                <div
                  key={`${message.role}-${index}`}
                  className={message.role === 'user' ? 'ml-auto max-w-[85%]' : 'mr-auto max-w-[85%]'}
                >
                  <div
                    className={
                      message.role === 'user'
                        ? 'rounded-[var(--ui-radius-lg)] bg-[var(--ui-primary)] px-4 py-3 text-sm font-medium text-white shadow-[0_10px_24px_rgba(234,106,42,0.24)]'
                        : 'rounded-[var(--ui-radius-lg)] border border-[var(--ui-border)] bg-white px-4 py-3 text-sm text-[var(--ui-text)] shadow-[var(--ui-shadow-sm)]'
                    }
                  >
                    <div className="mb-1 text-[11px] font-bold uppercase tracking-[0.12em] opacity-70">
                      {message.role === 'user' ? 'You' : 'Assistant'}
                    </div>
                    <div className="whitespace-pre-wrap">{message.content}</div>
                  </div>
                </div>
              ))
            )}

            {streamingText ? (
              <div className="mr-auto max-w-[85%] rounded-[var(--ui-radius-lg)] border border-[var(--ui-border)] bg-white px-4 py-3 text-sm text-[var(--ui-text)] shadow-[var(--ui-shadow-sm)]">
                <div className="mb-1 text-[11px] font-bold uppercase tracking-[0.12em] opacity-70">Assistant</div>
                <div className="whitespace-pre-wrap">{streamingText}</div>
              </div>
            ) : null}

            {sending && !streamingText ? (
              <div className="mr-auto max-w-[85%] rounded-[var(--ui-radius-lg)] border border-[var(--ui-border)] bg-white px-4 py-3 text-sm text-[var(--ui-text-secondary)] shadow-[var(--ui-shadow-sm)]">
                Assistant is thinking…
              </div>
            ) : null}
            <div ref={messagesEndRef} />
          </div>
        </ChatLayout>
      </div>
    </PageLayout>
  );
}

export default function ChatPage() {
  return (
    <ProtectedRoute>
      <ChatContent />
    </ProtectedRoute>
  );
}
