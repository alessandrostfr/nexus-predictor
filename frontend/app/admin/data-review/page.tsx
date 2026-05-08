'use client';

import { useEffect, useMemo, useState } from 'react';

type ApiResponse<T> = {
  success: boolean;
  message?: string;
  data: T;
};

type Coverage = {
  ready: boolean;
  masters: number;
  aliases: number;
  links: number;
  candidates: number;
  pending_candidates: number;
  feature_eligible_links: number;
  low_confidence_feature_links: number;
  minimum_feature_confidence: string[];
  warnings: string[];
};

type Candidate = {
  id: number;
  canonical_artist_key: string;
  platform: string;
  candidate_name: string;
  candidate_url?: string | null;
  match_score: number;
  confidence: string;
  status: string;
  suggested_action: string;
  review_notes?: string | null;
};

type CandidateList = {
  total: number;
  items: Candidate[];
};

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://127.0.0.1:8000/api';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(options?.headers ?? {}),
    },
    cache: 'no-store',
  });
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status}`);
  }
  const payload = (await response.json()) as ApiResponse<T>;
  if (payload.success === false) {
    throw new Error(payload.message ?? 'API returned success=false');
  }
  return payload.data;
}

export default function DataReviewPage() {
  const [coverage, setCoverage] = useState<Coverage | null>(null);
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reviewingId, setReviewingId] = useState<number | null>(null);

  async function loadData() {
    setLoading(true);
    setError(null);
    try {
      const [coveragePayload, candidatePayload] = await Promise.all([
        request<Coverage>('/v3/identity/coverage'),
        request<CandidateList>('/v3/identity/candidates?status=pending_review&limit=25'),
      ]);
      setCoverage(coveragePayload);
      setCandidates(candidatePayload.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }

  async function review(candidateId: number, decision: 'verified' | 'rejected') {
    setReviewingId(candidateId);
    setError(null);
    try {
      await request(`/v3/identity/candidates/${candidateId}/review`, {
        method: 'POST',
        body: JSON.stringify({
          decision,
          confidence: decision === 'verified' ? 'high' : 'rejected',
          reviewed_by: 'frontend_admin',
          notes: decision === 'verified' ? 'Reviewed from admin data-review UI.' : 'Rejected from admin data-review UI.',
        }),
      });
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setReviewingId(null);
    }
  }

  useEffect(() => {
    void loadData();
  }, []);

  const gateLabel = useMemo(() => coverage?.minimum_feature_confidence.join(' / ') ?? 'verified / high', [coverage]);

  return (
    <main style={{ minHeight: '100vh', padding: '32px', background: 'radial-gradient(circle at top, rgba(163,255,18,.16), transparent 28%), #050508', color: '#fff' }}>
      <section style={{ maxWidth: '1120px', margin: '0 auto', display: 'grid', gap: '24px' }}>
        <div style={{ display: 'grid', gap: '10px' }}>
          <a href="/" style={{ color: '#a3ff12', textDecoration: 'none', fontWeight: 700 }}>← Volver al dashboard</a>
          <p style={{ margin: 0, color: '#a3ff12', fontWeight: 800, letterSpacing: '.16em', textTransform: 'uppercase' }}>V3.3 · Admin data review</p>
          <h1 style={{ margin: 0, fontSize: 'clamp(2.2rem, 6vw, 4.8rem)', lineHeight: .95 }}>Identity resolution</h1>
          <p style={{ maxWidth: '760px', color: '#b7bad6', fontSize: '1rem', lineHeight: 1.7 }}>
            Revisa candidatos de perfiles externos antes de permitir que sus métricas alimenten features ML. El gate actual solo acepta enlaces {gateLabel}.
          </p>
        </div>

        {error ? <div style={{ padding: '16px', border: '1px solid rgba(255,56,100,.45)', borderRadius: '18px', background: 'rgba(255,56,100,.1)' }}>{error}</div> : null}

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '12px' }}>
          {[
            ['Canonical artists', coverage?.masters ?? 0],
            ['Aliases', coverage?.aliases ?? 0],
            ['Identity links', coverage?.links ?? 0],
            ['Pending review', coverage?.pending_candidates ?? 0],
            ['Feature eligible', coverage?.feature_eligible_links ?? 0],
            ['Low-confidence eligible', coverage?.low_confidence_feature_links ?? 0],
          ].map(([label, value]) => (
            <article key={label} style={{ padding: '18px', border: '1px solid rgba(255,255,255,.12)', borderRadius: '22px', background: 'rgba(255,255,255,.06)' }}>
              <p style={{ margin: '0 0 8px', color: '#777b9f', fontSize: '.78rem', textTransform: 'uppercase', letterSpacing: '.08em' }}>{label}</p>
              <strong style={{ fontSize: '2rem' }}>{value}</strong>
            </article>
          ))}
        </div>

        <section style={{ padding: '22px', border: '1px solid rgba(255,255,255,.12)', borderRadius: '28px', background: 'rgba(255,255,255,.06)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: '16px', alignItems: 'center', flexWrap: 'wrap' }}>
            <div>
              <h2 style={{ margin: 0 }}>Candidatos pendientes</h2>
              <p style={{ margin: '8px 0 0', color: '#b7bad6' }}>Verifica solo perfiles realmente oficiales o claramente correctos.</p>
            </div>
            <button onClick={loadData} style={{ border: 0, borderRadius: '999px', padding: '12px 18px', fontWeight: 800, background: '#a3ff12', color: '#061010', cursor: 'pointer' }}>Refrescar</button>
          </div>

          {loading ? <p style={{ color: '#b7bad6' }}>Cargando candidatos…</p> : null}
          {!loading && candidates.length === 0 ? <p style={{ color: '#b7bad6' }}>No hay candidatos pendientes. Buen estado para V3.4.</p> : null}

          <div style={{ display: 'grid', gap: '12px', marginTop: '18px' }}>
            {candidates.map((candidate) => (
              <article key={candidate.id} style={{ display: 'grid', gap: '12px', padding: '16px', border: '1px solid rgba(255,255,255,.12)', borderRadius: '20px', background: 'rgba(0,0,0,.24)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px', flexWrap: 'wrap' }}>
                  <div>
                    <strong>{candidate.candidate_name}</strong>
                    <p style={{ margin: '6px 0 0', color: '#b7bad6' }}>{candidate.canonical_artist_key} · {candidate.platform} · score {Math.round(candidate.match_score * 100)}% · {candidate.confidence}</p>
                    {candidate.candidate_url ? <a href={candidate.candidate_url} target="_blank" rel="noreferrer" style={{ color: '#22d3ee' }}>{candidate.candidate_url}</a> : null}
                  </div>
                  <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                    <button disabled={reviewingId === candidate.id} onClick={() => review(candidate.id, 'verified')} style={{ border: 0, borderRadius: '999px', padding: '10px 14px', fontWeight: 800, background: '#34d399', color: '#04130e', cursor: 'pointer' }}>Verificar</button>
                    <button disabled={reviewingId === candidate.id} onClick={() => review(candidate.id, 'rejected')} style={{ border: 0, borderRadius: '999px', padding: '10px 14px', fontWeight: 800, background: '#ff3864', color: '#fff', cursor: 'pointer' }}>Rechazar</button>
                  </div>
                </div>
              </article>
            ))}
          </div>
        </section>
      </section>
    </main>
  );
}
