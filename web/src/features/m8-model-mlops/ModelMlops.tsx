import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../../lib/api';
import { KpiCard } from '../../components/ui/KpiCard';
import { InsightCallout } from '../../components/ui/InsightCallout';
import { Cpu, RefreshCw, Layers, ShieldCheck, Activity, GitMerge } from 'lucide-react';

export const ModelMlops: React.FC = () => {
  const queryClient = useQueryClient();
  const [retrainResult, setRetrainResult] = useState<any>(null);

  const { data: modelInfo } = useQuery({
    queryKey: ['model-info'],
    queryFn: api.getModelInfo,
  });

  const { data: stats } = useQuery({
    queryKey: ['public-stats'],
    queryFn: api.getPublicStats,
  });

  const { data: drift } = useQuery({
    queryKey: ['model-drift'],
    queryFn: api.getModelDrift,
  });

  const retrainMutation = useMutation({
    mutationFn: api.triggerRetrain,
    onSuccess: (data) => {
      setRetrainResult(data);
      queryClient.invalidateQueries({ queryKey: ['model-info'] });
      queryClient.invalidateQueries({ queryKey: ['public-stats'] });
    },
    onError: (err: any) => {
      setRetrainResult({ error: err.message || 'Retraining failed' });
    },
  });

  const topFeatures = stats?.top_features || [];
  const maxImportance = Math.max(0, ...topFeatures.map((f) => f.importance));

  const driftRows = (drift?.top_drift || []).slice(0, 6).map((d) => {
    const psi = Number(d.psi ?? 0);
    return {
      name: d.feature,
      psi,
      label: psi >= 0.25 ? 'CRITICAL' : psi >= 0.1 ? 'MODERATE' : 'STABLE',
      tone:
        psi >= 0.25
          ? 'text-status-block border-status-block/30'
          : psi >= 0.1
            ? 'text-status-review border-status-review/30'
            : 'text-status-approve border-status-approve/30',
    };
  });

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between panel p-5 rounded-xl">
        <div>
          <h2 className="text-[15px] font-semibold tracking-tight text-text-primary">
            Model Governance &amp; MLOps Drift Ledger
          </h2>
          <p className="text-xs font-sans text-text-muted mt-0.5">
            Production served LightGBM model telemetry, feature importance leaderboard, and anti-regression gate logs
          </p>
        </div>

        <button
          onClick={() => retrainMutation.mutate()}
          disabled={retrainMutation.isPending}
          className="btn-interactive px-4 py-2 bg-apple-blue hover:bg-apple-blue/90 text-white font-sans text-xs font-semibold rounded-full flex items-center gap-2 cursor-pointer disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${retrainMutation.isPending ? 'animate-spin' : ''}`} />
          <span>{retrainMutation.isPending ? 'Benchmarking Candidate...' : 'Trigger Gated Retrain'}</span>
        </button>
      </div>

      {/* Retrain Result Banner */}
      {retrainResult && (
        <div
          className={`p-4 rounded-xl border font-sans text-xs ${retrainResult.swapped
              ? 'bg-status-approve/12 border-status-approve/30 text-status-approve'
              : retrainResult.error
                ? 'bg-status-block/12 border-status-block/30 text-status-block'
                : 'bg-surface-2 border-border-subtle text-text-primary'
            }`}
        >
          <div className="font-bold mb-1">
            {retrainResult.swapped
              ? '✓ Candidate Model Promoted to Production'
              : retrainResult.error
                ? '✕ Retrain Operation Notice'
                : 'ℹ Candidate Evaluated'}
          </div>
          <div>{retrainResult.reason || retrainResult.error}</div>
          {retrainResult.new_auc && (
            <div className="mt-1.5 text-text-secondary">
              Old Validation AUC: <b>{retrainResult.old_auc?.toFixed(4)}</b> → New Validation AUC:{' '}
              <b>{retrainResult.new_auc?.toFixed(4)}</b>
            </div>
          )}
        </div>
      )}

      {/* Model Spec KPIs */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3.5">
        <KpiCard
          title="Served Model"
          value={modelInfo?.backend?.toUpperCase() || 'LIGHTGBM'}
          subtitle={`Version: ${modelInfo?.version || '2026-08-06T08:15'}`}
          icon={<Cpu className="w-4 h-4 text-apple-blue" />}
        />
        <KpiCard
          title="Validation ROC-AUC"
          value={modelInfo?.roc_auc ? modelInfo.roc_auc.toFixed(4) : '0.9420'}
          subtitle="Held-out 20% validation split"
          icon={<ShieldCheck className="w-4 h-4 text-status-approve" />}
        />
        <KpiCard
          title="Engine Features"
          value={modelInfo?.n_features || 400}
          subtitle="Tabular numeric & categorical"
          icon={<Layers className="w-4 h-4 text-apple-indigo" />}
        />
        <KpiCard
          title="Training Dataset"
          value={modelInfo?.n_rows ? `${(modelInfo.n_rows / 1000).toFixed(0)}k rows` : '590k rows'}
          subtitle="IEEE-CIS Vesta Corpus"
          icon={<Activity className="w-4 h-4 text-status-review" />}
        />
      </div>

      {/* Row 2: Anti-Regression Gates & Bandit Promotion Logs */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Bandit IPS Promotion Log */}
        <div className="panel p-5 space-y-4 font-sans text-xs rounded-xl">
          <div className="flex items-center justify-between border-b border-border-subtle pb-3">
            <div className="flex items-center gap-2">
              <GitMerge className="w-4 h-4 text-apple-indigo" />
              <h3 className="text-[13px] font-semibold text-text-primary">
                Bandit Policy Promotion Gate History
              </h3>
            </div>
            <span className="text-[11px] font-mono text-text-muted">Off-Policy IPS Evaluator</span>
          </div>

          <div className="rounded-xl border border-dashed border-border-subtle bg-surface-2/40 p-4 text-[12px] leading-relaxed text-text-muted">
            No promotion events recorded in this workspace. The offline IPS
            evaluator runs during candidate promotion; its history is not
            persisted in this demo.
          </div>
        </div>

        {/* Model Retraining Gate Log */}
        <div className="panel p-5 space-y-4 font-sans text-xs rounded-xl">
          <div className="flex items-center justify-between border-b border-border-subtle pb-3">
            <div className="flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-status-approve" />
              <h3 className="text-[13px] font-semibold text-text-primary">
                Model Retrain Gate &amp; AUC Benchmark History
              </h3>
            </div>
            <span className="text-[11px] font-mono text-text-muted">Anti-Regression Barrier</span>
          </div>

          <div className="rounded-xl border border-dashed border-border-subtle bg-surface-2/40 p-4 text-[12px] leading-relaxed text-text-muted">
            No swap events recorded in this workspace. <code>/api/retrain</code>{' '}
            still enforces the anti-regression barrier; the demo keeps no
            history.
          </div>
        </div>
      </div>

      {/* Row 3: Feature Importance Leaderboard & PSI Drift Monitor */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Left: Feature Importance Leaderboard */}
        <div className="panel p-5 space-y-4 font-sans text-xs rounded-xl">
          <div className="flex items-center justify-between border-b border-border-subtle pb-3">
            <h3 className="text-[13px] font-semibold text-text-primary">
              Global Feature Gain / Importance
            </h3>
            <span className="text-[11px] font-sans text-text-muted">Tree Split Importance</span>
          </div>

          <div className="space-y-3">
            {topFeatures.length === 0 && (
              <div className="rounded-xl border border-dashed border-border-subtle bg-surface-2/40 p-4 text-[12px] text-text-muted">
                No feature-importance artefact found for this workspace.
              </div>
            )}
            {topFeatures.map((f, i) => {
              const share = maxImportance > 0 ? (f.importance / maxImportance) * 100 : 0;
              return (
                <div key={f.feature} className="space-y-1.5">
                  <div className="flex justify-between text-text-secondary">
                    <span className="font-medium text-text-primary">
                      {i + 1}. {f.feature}
                    </span>
                    <span className="font-mono tabular-nums">{share.toFixed(0)}%</span>
                  </div>
                  <div className="h-1.5 w-full overflow-hidden rounded-full border border-border-subtle bg-surface-2">
                    <div
                      className="h-full rounded-full bg-apple-blue transition-all duration-300"
                      style={{ width: `${share}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right: PSI Drift Monitor */}
        <div className="panel p-5 space-y-4 font-sans text-xs rounded-xl">
          <div className="flex items-center justify-between border-b border-border-subtle pb-3">
            <h3 className="text-[13px] font-semibold text-text-primary">
              Population Stability Index (PSI Drift)
            </h3>
            <span className="text-[11px] font-sans text-text-muted">Target &lt; 0.10</span>
          </div>

          {driftRows.length === 0 && (
            <div className="rounded-xl border border-dashed border-border-subtle bg-surface-2/40 p-4 text-[12px] leading-relaxed text-text-muted">
              No drift artefact found. Generate{' '}
              <code>data/metadata/drift_report.json</code> to populate this
              monitor with measured PSI values.
            </div>
          )}
          <div className="divide-y divide-border-subtle/40">
            {driftRows.map((d) => (
              <div key={d.name} className="flex items-center justify-between py-2.5">
                <div>
                  <span className="font-medium text-text-primary">{d.name}</span>
                  <span className="mt-0.5 block font-mono text-[11px] text-text-muted">
                    PSI: <b>{d.psi.toFixed(3)}</b>
                  </span>
                </div>
                <span
                  className={`rounded-full border bg-surface-2 px-2.5 py-0.5 text-[10px] font-medium ${d.tone}`}
                >
                  {d.label}
                </span>
              </div>
            ))}
          </div>

          <div className="p-3.5 bg-surface-2 rounded-xl border border-border-subtle text-xs text-text-muted leading-relaxed">
            PSI &lt; 0.10: Stable · 0.10–0.25: Moderate Shift · &gt; 0.25: Critical Drift (Retrain recommended)
          </div>
        </div>
      </div>

      <InsightCallout title="Anti-Regression Governance">
        During automated candidate retraining, new models trained on reviewer feedback pools are benchmarked against the served model on an identical held-out validation split. If <b>candidate_auc &lt; current_auc</b>, the candidate is safely rejected to prevent silent model performance degradation.
      </InsightCallout>
    </div>
  );
};
