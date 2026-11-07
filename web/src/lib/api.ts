import type {
  DecisionItem,
  MetricsSummary,
  TimeseriesBucket,
  MetricsDispositions,
  MetricsLoss,
  MetricsRule,
  ModelDrift,
  PolicyInfo,
  BanditStatus,
  ExplainResponse,
  ModelInfo,
  HealthResponse,
  SimulateRequest,
  SimulateResponse,
  BatchScoreResponse,
} from './types';

export const BASE_URL =
  import.meta.env.VITE_API_URL ||
  (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
    ? ''
    : 'https://p-quincy-fraud-detection-dashboard-simulation.hf.space');

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const timeoutMs = 15000;
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs);
  let res: Response;
  try {
    res = await fetch(`${BASE_URL}${url}`, {
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
      ...options,
      signal: controller.signal,
    });
  } finally {
    window.clearTimeout(timeoutId);
  }
  if (!res.ok) {
    let errorDetail = `HTTP ${res.status}: ${res.statusText}`;
    try {
      const err = await res.json();
      if (err.detail) errorDetail = typeof err.detail === 'string' ? err.detail : JSON.stringify(err.detail);
    } catch {
      // ignore
    }
    throw new Error(errorDetail);
  }
  return res.json() as Promise<T>;
}

export const api = {
  getHealth: () => fetchJson<HealthResponse>('/api/health'),
  getModelInfo: () => fetchJson<ModelInfo>('/api/model'),
  getPublicStats: () => fetchJson<{ model: ModelInfo; overview: Record<string, unknown>; top_features: Array<{ feature: string; importance: number }> }>('/api/stats'),
  
  getMetricsSummary: () => fetchJson<MetricsSummary>('/api/metrics/summary'),
  getModelDrift: () => fetchJson<ModelDrift>('/api/model/drift'),
  getMetricsTimeseries: (windowMinutes = 60, bucketSeconds = 60) =>
    fetchJson<TimeseriesBucket[]>(`/api/metrics/timeseries?w=${windowMinutes}&bucket=${bucketSeconds}`),
  getMetricsDispositions: () => fetchJson<MetricsDispositions>('/api/metrics/dispositions'),
  getMetricsLoss: () => fetchJson<MetricsLoss>('/api/metrics/loss'),
  getMetricsRules: () => fetchJson<MetricsRule[]>('/api/metrics/rules'),

  getReviewQueue: (status = 'NEW', limit = 100, decision?: string) =>
    fetchJson<DecisionItem[]>(
      `/api/review/queue?status=${encodeURIComponent(status)}&limit=${encodeURIComponent(String(limit))}${decision ? `&decision=${encodeURIComponent(decision)}` : ''}`,
    ),
  getPolicy: () => fetchJson<PolicyInfo>('/api/policy'),
  getBanditStatus: () => fetchJson<BanditStatus>('/api/bandit/status'),
  getReviewItem: (transactionId: string) =>
    fetchJson<DecisionItem>(`/api/review/${encodeURIComponent(transactionId)}`),
  getAuditReport: (transactionId: string) =>
    fetchJson<{ transaction_id: string; report: string; source: string; generated_at: string }>(`/api/review/${encodeURIComponent(transactionId)}/report`),
  
  submitReviewOutcome: (transactionId: string, verdict: 'safe' | 'fraud', note?: string) =>
    fetchJson<DecisionItem>(`/api/review/${encodeURIComponent(transactionId)}/outcome`, {
      method: 'POST',
      body: JSON.stringify({ verdict, note }),
    }),
  appealDecision: (transactionId: string, note?: string) =>
    fetchJson<DecisionItem>(`/api/review/${encodeURIComponent(transactionId)}/appeal`, {
      method: 'POST',
      body: JSON.stringify({ note }),
    }),

  simulate: (req: SimulateRequest) =>
    fetchJson<SimulateResponse>('/api/simulate', {
      method: 'POST',
      body: JSON.stringify(req),
    }),
  explain: (values: Record<string, number>) =>
    fetchJson<ExplainResponse>('/api/explain', {
      method: 'POST',
      body: JSON.stringify({ values }),
    }),
  predictBatch: async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    const controller = new AbortController();
    const timeoutId = window.setTimeout(() => controller.abort(), 60000);
    let res: Response;
    try {
      res = await fetch(`${BASE_URL}/api/predict/batch`, {
        method: 'POST',
        body: formData,
        signal: controller.signal,
      });
    } finally {
      window.clearTimeout(timeoutId);
    }
    if (!res.ok) {
      let errorDetail = `Batch upload failed: ${res.statusText}`;
      try {
        const err = await res.json();
        if (err.detail) errorDetail = typeof err.detail === 'string' ? err.detail : JSON.stringify(err.detail);
      } catch { /* ignore */ }
      throw new Error(errorDetail);
    }
    return res.json() as Promise<BatchScoreResponse>;
  },
  triggerRetrain: () =>
    fetchJson<{ swapped: boolean; old_auc: number; new_auc: number; reason: string }>('/api/retrain', {
      method: 'POST',
    }),
};
