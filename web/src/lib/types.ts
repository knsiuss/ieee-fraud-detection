export type DecisionType = 'APPROVE' | 'MANUAL_REVIEW' | 'DECLINE';
export type RiskTier = 'low' | 'medium' | 'high';
export type ReviewerOutcome = 'safe' | 'fraud' | null;

export interface DecisionItem {
  transaction_id: string;
  timestamp: string;
  model_version: string;
  contract_version?: string;
  score: number;
  decision: DecisionType;
  action?: string;
  policy_version?: string;
  thresholds?: {
    approve?: number;
    decline?: number;
    upper?: number;
    lower?: number;
  };
  reason_codes?: Array<{
    code: string;
    description: string;
    feature?: string;
    contribution?: number;
  }>;
  feature_report?: {
    latency_ms?: number;
    features_present?: number;
    features_missing?: number;
    [key: string]: unknown;
  };
  input_features?: Record<string, number | string>;
  status?: string;
  reviewer_outcome?: ReviewerOutcome;
  feedback_note?: string;
}

export interface MetricsSummary {
  total_decisions: number;
  counts: {
    APPROVE: number;
    MANUAL_REVIEW: number;
    DECLINE: number;
  };
  percentages: {
    APPROVE: number;
    MANUAL_REVIEW: number;
    DECLINE: number;
  };
  avg_score: number;
  gmv_total: number;
  loss_prevented: number;
  loss_under_review: number;
  tps: number;
  latency: {
    p50_ms: number;
    p95_ms: number;
    p99_ms: number;
  };
  psi_drift: number;
  chargeback_bps: number;
  sla_bands: {
    under_1h: number;
    under_4h: number;
    over_4h: number;
  };
  sla_compliance_pct: number | null;
  epoch: string;
}

export interface TimeseriesBucket {
  timestamp: string;
  total: number;
  approved: number;
  reviewed: number;
  declined: number;
  amount_sum: number;
  avg_score: number;
}

export interface MetricsDispositions {
  total_decisions: number;
  total_reviewed: number;
  confirmed_fraud: number;
  false_positives: number;
  leakage: number;
  analyst_confirm_rate: number;
  false_positive_rate: number;
  disposition_mix: {
    confirmed_fraud: number;
    overturned_safe: number;
    escalated: number;
  };
}

export interface MetricsLoss {
  total_gmv: number;
  loss_prevented: number;
  under_review_exposure: number;
  cleared_safe_volume: number;
  fraud_prevention_roi: number;
  chargeback_bps: number;
  network_threshold_bps: number;
}

export interface MetricsRule {
  feature: string;
  label: string;
  occurrences: number;
  avg_contribution: number;
  max_contrib: number;
  blocked: number;
  blocked_amount: number;
  weighted_blocked: number;
  severity: 'high' | 'medium' | 'low';
}

export interface ShapDriver {
  feature: string;
  label: string;
  value: number | null;
  typical: number | null;
  value_text: string;
  typical_text: string;
  contribution: number;
  direction: 'fraud' | 'safe';
}

export interface ShapFeature {
  feature: string;
  contribution: number;
  direction: 'fraud' | 'safe';
}

export interface ExplainResponse {
  probability: number;
  risk_tier: RiskTier;
  action: string;
  model_version: string;
  summary: string;
  drivers: ShapDriver[];
  features: ShapFeature[];
}

export interface ModelInfo {
  version: string;
  status: string;
  backend?: string;
  roc_auc?: number;
  train_auc?: number;
  n_rows?: number;
  n_features?: number;
  trained_at?: string;
  [key: string]: unknown;
}

export interface HealthResponse {
  status: string;
  model_present: boolean;
  model_version?: string | null;
}

export interface SimulateRequest {
  profile: 'typical' | 'nonfraud' | 'fraud';
  transaction_id?: string;
  amount?: number;
  card_brand?: string;
  billing_distance?: number;
  card_match_count?: number;
  purchase_frequency?: number;
  days_since_activity?: number;
}

export interface SimulateResponse {
  probability: number;
  risk_tier: RiskTier;
  action: string;
  model_version: string;
  transaction_id: string;
  decision: DecisionType;
  policy_version: string;
  contract_version: string;
  feature_report: Record<string, unknown>;
  profile: string;
  mapped_values: Record<string, number>;
  feature_usage: Record<string, unknown>;
}

export interface BatchScoreRow {
  id?: string | number;
  transaction_id?: string;
  probability: number;
  risk_tier: RiskTier;
  action: string;
  decision?: DecisionType;
  policy_version?: string;
  contract_version?: string;
}

export interface BatchScoreResponse {
  model_version: string;
  count: number;
  rows: BatchScoreRow[];
  errors: Array<{ [key: string]: string }>;
}
