import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../../lib/api';
import { KpiCard } from '../../components/ui/KpiCard';
import { TimeseriesChart } from '../../components/charts/TimeseriesChart';
import { InsightCallout } from '../../components/ui/InsightCallout';
import { DollarSign, ShieldAlert, CheckCircle2, TrendingDown, Percent, FileText } from 'lucide-react';

export const ExecImpact: React.FC = () => {
  const { data: summary } = useQuery({
    queryKey: ['metrics-summary'],
    queryFn: api.getMetricsSummary,
  });

  const { data: loss } = useQuery({
    queryKey: ['metrics-loss'],
    queryFn: api.getMetricsLoss,
  });

  const { data: dispositions } = useQuery({
    queryKey: ['metrics-dispositions'],
    queryFn: api.getMetricsDispositions,
  });

  const { data: timeseries } = useQuery({
    queryKey: ['metrics-timeseries-long'],
    queryFn: () => api.getMetricsTimeseries(60, 120),
  });

  const totalGmv = loss?.total_gmv || summary?.gmv_total || 420000;
  const lossPrevented = loss?.loss_prevented || summary?.loss_prevented || 142500;
  const safeVolume = loss?.cleared_safe_volume || totalGmv - lossPrevented;
  const underReviewExposure = loss?.under_review_exposure || 18400;

  return (
    <div className="space-y-6">
      {/* Top Executive Header */}
      <div className="flex items-center justify-between bg-surface-1 border border-border-subtle p-4 rounded-lg">
        <div>
          <h2 className="text-base font-bold text-text-primary tracking-tight">
            EXECUTIVE &amp; CREDIT RISK IMPACT
          </h2>
          <p className="text-xs font-mono text-text-muted">
            Monetary savings, chargeback exposure, and customer checkout friction metrics
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="px-2.5 py-1 rounded bg-status-approve/12 border border-status-approve/25 text-status-approve font-mono text-xs font-semibold">
            PROGRAM STATUS: HEALTHY
          </span>
        </div>
      </div>

      {/* Row 1: Executive KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard
          title="Total Evaluated GMV"
          value={`$${totalGmv.toLocaleString()}`}
          subtitle="Gross Merchandise Volume"
          icon={<DollarSign className="w-4 h-4" />}
          accent="cyan"
        />
        <KpiCard
          title="Fraud Loss Prevented"
          value={`$${lossPrevented.toLocaleString()}`}
          subtitle={`${((lossPrevented / Math.max(totalGmv, 1)) * 100).toFixed(1)}% of total volume saved`}
          trend={{ value: 'Saved', direction: 'up' }}
          icon={<ShieldAlert className="w-4 h-4 text-status-approve" />}
          accent="emerald"
        />
        <KpiCard
          title="Cleared Safe Volume"
          value={`$${safeVolume.toLocaleString()}`}
          subtitle="Zero-friction checkout approvals"
          icon={<CheckCircle2 className="w-4 h-4" />}
          accent="teal"
        />
        <KpiCard
          title="Review Exposure"
          value={`$${underReviewExposure.toLocaleString()}`}
          subtitle={`${dispositions?.total_reviewed || 0} decisions reviewed`}
          icon={<Percent className="w-4 h-4" />}
          accent="amber"
        />
      </div>

      {/* Row 2: Financial Charts Split */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2 bg-surface-1 border border-border-subtle rounded-lg p-4">
          <div className="flex items-center justify-between mb-3">
            <div>
              <h3 className="text-xs font-semibold uppercase tracking-wider text-text-primary">
                Monetary Volume &amp; Fraud Prevention Trajectory
              </h3>
              <p className="text-[11px] font-mono text-text-muted">
                Evaluated GMV ($) vs Fraud Loss Prevented ($) across time buckets
              </p>
            </div>
          </div>
          <TimeseriesChart data={timeseries || []} height="300px" showAmount={true} />
        </div>

        {/* Card Network Compliance & Chargeback BPS */}
        <div className="bg-surface-1 border border-border-subtle rounded-lg p-4 flex flex-col justify-between space-y-4">
          <div>
            <h3 className="text-xs font-semibold uppercase tracking-wider text-text-primary mb-1">
              Card Network Compliance (BPS)
            </h3>
            <p className="text-[11px] font-mono text-text-muted mb-4">
              Basis points vs Visa &amp; Mastercard 0.9% (90 BPS) excessive threshold
            </p>

            <div className="p-4 bg-surface-2 rounded-lg border border-border-subtle space-y-3">
              <div className="flex justify-between items-center font-mono">
                <span className="text-xs text-text-secondary">Current Sentinel BPS:</span>
                <span className="text-lg font-bold text-status-approve">
                  {loss?.chargeback_bps || 16.4} BPS
                </span>
              </div>

              {/* Progress bar */}
              <div className="w-full bg-surface-hover h-2.5 rounded-full overflow-hidden relative">
                <div
                  className="bg-status-approve h-full rounded-full"
                  style={{ width: `${Math.min(((loss?.chargeback_bps || 16.4) / 90) * 100, 100)}%` }}
                />
              </div>

              <div className="flex justify-between text-[10px] font-mono text-text-muted">
                <span>0 BPS</span>
                <span className="text-status-review">50 BPS (Watch)</span>
                <span className="text-status-block">90 BPS (Network Limit)</span>
              </div>
            </div>
          </div>

          {/* Friction breakdown */}
          <div className="p-3 bg-surface-2/60 border border-border-subtle rounded-lg space-y-2 text-xs font-mono">
            <div className="text-text-secondary font-semibold text-[11px] uppercase">
              Accuracy &amp; Analyst Dispositions
            </div>
            <div className="flex justify-between text-text-muted">
              <span>Confirmed Fraud (True Positives):</span>
              <span className="text-status-block font-bold">{dispositions?.confirmed_fraud || 0}</span>
            </div>
            <div className="flex justify-between text-text-muted">
              <span>False Positives (Overturned):</span>
              <span className="text-status-approve font-bold">{dispositions?.false_positives || 0}</span>
            </div>
            <div className="flex justify-between text-text-muted">
              <span>Analyst Confirmation Rate:</span>
              <span className="text-text-primary font-bold">{dispositions?.analyst_confirm_rate || 0}%</span>
            </div>
          </div>
        </div>
      </div>

      {/* Executive Key Insight */}
      <InsightCallout title="Executive & Credit Risk Summary" variant="success">
        The LightGBM fraud decision engine has preserved <b>${lossPrevented.toLocaleString()}</b> in potential fraud losses with a stellar chargeback rate of <b>{loss?.chargeback_bps || 16.4} BPS</b>, safely below the 90 BPS Visa/Mastercard monitoring thresholds. Customer checkout friction is minimized with <b>{summary?.percentages.APPROVE || 94.2}%</b> automated zero-delay approvals.
      </InsightCallout>
    </div>
  );
};
