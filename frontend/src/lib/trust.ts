export type PortfolioTrustState =
  | 'no_identity'
  | 'identity_present_unverified'
  | 'verified'
  | 'manual_review'
  | 'revoked_or_blocked';

export interface TrustVerificationSummary {
  document_type: 'aadhaar' | 'pan';
  verification_id: string;
  workflow_status: 'pending' | 'processing' | 'verified' | 'failed' | 'manual_review';
  decision?: 'approve' | 'reject' | 'manual_review' | null;
  reason?: string | null;
}

export interface TrustSurface {
  trust_version: 'v1';
  wallet_address: string;
  did: string;
  verification_bitmap: number;
  updated_at: string;
  trust_state: Exclude<PortfolioTrustState, 'no_identity'>;
  high_trust_eligible: boolean;
  state_reason?: string | null;
  verifications: TrustVerificationSummary[];
}

export interface TrustSnapshot {
  state: PortfolioTrustState;
  eligible: boolean;
  reason: string | null;
  trust: TrustSurface | null;
}

const LOCAL_IDENTITY_WEB_URL = 'http://127.0.0.1:43100';
const DEPLOYED_IDENTITY_WEB_URL = 'https://aadharcha.in';
const LOCAL_TRUST_API_URL = 'http://127.0.0.1:43101';
const DEPLOYED_TRUST_API_URL = 'https://identity-aadhar-gateway.onrender.com';

export function resolveIdentityWebUrl(): string {
  if (typeof window !== 'undefined') {
    const { hostname } = window.location;
    if (hostname === 'localhost' || hostname === '127.0.0.1') {
      return process.env.NEXT_PUBLIC_IDENTITY_WEB_URL || LOCAL_IDENTITY_WEB_URL;
    }
  }

  return process.env.NEXT_PUBLIC_IDENTITY_WEB_URL || DEPLOYED_IDENTITY_WEB_URL;
}

export function resolveTrustApiUrl(): string {
  if (typeof window !== 'undefined') {
    const { hostname } = window.location;
    if (hostname === 'localhost' || hostname === '127.0.0.1') {
      return process.env.NEXT_PUBLIC_TRUST_API_URL || LOCAL_TRUST_API_URL;
    }
  }

  return process.env.NEXT_PUBLIC_TRUST_API_URL || DEPLOYED_TRUST_API_URL;
}

const TRUST_API_URL = resolveTrustApiUrl();

async function fetchJson<T>(url: string): Promise<T> {
  const response = await fetch(url, { credentials: 'include' });
  if (!response.ok) {
    throw new Error(`Trust API request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export async function fetchTrustSnapshot(subjectId: string): Promise<TrustSnapshot> {
  if (!subjectId) {
    return {
      state: 'no_identity',
      eligible: false,
      reason: 'Authenticate with AadhaarChain before using trust-gated transparency actions.',
      trust: null,
    };
  }

  const identityResponse = await fetchJson<{ data: unknown | null }>(
    `${TRUST_API_URL}/api/identity/${subjectId}`
  );

  if (!identityResponse.data) {
    return {
      state: 'no_identity',
      eligible: false,
      reason: 'Create an identity anchor in AadhaarChain before uploading evidence or filing challenges.',
      trust: null,
    };
  }

  const trustResponse = await fetchJson<{ data: TrustSurface }>(
    `${TRUST_API_URL}/api/identity/${subjectId}/trust`
  );
  const trust = trustResponse.data;

  return {
    state: trust.trust_state,
    eligible: trust.high_trust_eligible,
    reason: trust.state_reason ?? null,
    trust,
  };
}

export const IDENTITY_WEB_URL = resolveIdentityWebUrl();

export { TRUST_API_URL };
