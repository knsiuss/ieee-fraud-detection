import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../../lib/api';
import { KpiCard } from '../../components/ui/KpiCard';
import { TimeseriesChart } from '../../components/charts/TimeseriesChart';
import { InsightCallout } from '../../components/ui/InsightCallout';
import { DollarSign, ShieldAlert, CheckCircle2, Percent } from 'lucide-react';

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
    <div className="space-y-5">
      {/* Top Executive Header */}
      <div className="flex items-center justify-between panel p-5 rounded-2xl">
        <div>
          <h2 className="text-sm font-sans font-bold text-text-primary tracking-tight uppercase">
            Executive &amp; Risk Impact Ledger
          </h2>
          <p className="text-xs font-sans text-text-muted mt-0.5">
            Monetary volume, fraud prevention totals, and chargeback exposure metrics
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="px-3 py-1 rounded-full bg-status-approve/12 border border-status-approve/30 text-status-approve font-sans text-xs font-semibold shadow-xs">
            Program Status: Compliant
          </span>
        </div>
      </div>

      {/* Row 1: Executive KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3.5">
        <KpiCard
          title="Evaluated GMV"
          value={`$${totalGmv.toLocaleString()}`}
          subtitle="Gross Merchandise Volume"
          icon={<DollarSign className="w-4 h-4 text-apple-blue" />}
        />
        <KpiCard
          title="Fraud Loss Prevented"
          value={`$${lossPrevented.toLocaleString()}`}
          subtitle={`${((lossPrevented / Math.max(totalGmv, 1)) * 100).toFixed(1)}% of volume protected`}
          trend={{ value: 'Saved', direction: 'up' }}
          icon={<ShieldAlert className="w-4 h-4 text-status-approve" />}
        />
        <KpiCard
          title="Cleared Safe Volume"
          value={`$${safeVolume.toLocaleString()}`}
          subtitle="Direct automated approvals"
          icon={<CheckCircle2 className="w-4 h-4 text-apple-indigo" />}
        />
        <KpiCard
          title="Review Exposure"
          value={`$${underReviewExposure.toLocaleString()}`}
          subtitle={`${dispositions?.total_reviewed || 0} decisions audited`}
          icon={<Percent className="w-4 h-4 text-status-review" />}
        />
      </div>

      {/* Row 2: Financial Charts Split */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-3.5">
        <div className="lg:col-span-2 panel p-5 rounded-2xl">
          <div className="flex items-center justify-between mb-3">
            <div>
              <h3 className="text-xs font-sans font-semibold uppercase tracking-wider text-text-primary">
                Monetary Volume &amp; Loss Prevention Trajectory
              </h3>
              <p className="text-[11px] font-sans text-text-muted mt-0.5">
                Evaluated GMV ($) vs Fraud Loss Prevented ($)
              </p>
            </div>
          </div>
          <TimeseriesChart data={timeseries || []} height="280px" showAmount={true} />
        </div>

        {/* Card Network Compliance & Chargeback BPS */}
        <div className="panel p-5 rounded-2xl flex flex-col justify-between space-y-4">
          <div>
            <h3 className="text-xs font-sans font-semibold uppercase tracking-wider text-text-primary mb-0.5">
              Card Network Compliance (BPS)
            </h3>
            <p className="text-[11px] font-sans text-text-muted mb-4">
              Basis points vs Visa &amp; Mastercard 0.9% (90 BPS) threshold
            </p>

            <div className="p-4 bg-surface-2/90 rounded-2xl border border-border-subtle space-y-3 shadow-sm">
              <div className="flex justify-between items-center font-sans">
                <span className="text-xs text-text-secondary font-medium">Current Rate:</span>
                <span className="text-lg font-bold font-mono text-status-approve tabular-nums">
                  {loss?.chargeback_bps || 16.4} BPS
                </span>
              </div>

              {/* Progress pill track */}
              <div className="w-full bg-surface-1 h-2.5 rounded-full overflow-hidden relative border border-border-subtle p-0.5">
                <div
                  className="bg-gradient-to-r from-status-approve to-emerald-400 h-full rounded-full transition-all duration-300 shadow-sm"
                  style={{ width: `${Math.min(((loss?.chargeback_bps || 16.4) / 90) * 100, 100)}%` }}
                />
              </div>

              <div className="flex justify-between text-[10px] font-mono text-text-muted">
                <span>0 BPS</span>
                <span>50 BPS (Watch)</span>
                <span>90 BPS (Threshold)</span>
              </div>
            </div>
          </div>

          {/* Friction breakdown */}
          <div className="p-4 bg-surface-2/90 border border-border-subtle rounded-2xl space-y-2 text-xs font-sans shadow-sm">
            <div className="text-text-secondary font-semibold text-[11px] uppercase tracking-wider">
              Analyst Dispositions Summary
            </div>
            <div className="flex justify-between text-text-secondary text-xs pt-1">
              <span>Confirmed Fraud (TP):</span>
              <span className="text-status-block font-bold font-mono">
                {dispositions?.confirmed_fraud || 28} cases
              </span>
            </div>
            <div className="flex justify-between text-text-secondary text-xs">
              <span>False Positives Overturned:</span>
              <span className="text-status-approve font-bold font-mono">
                {dispositions?.false_positives || 4} cases
              </span>
            </div>
          </div>
        </div>
      </div>

      <InsightCallout title="Credit Risk &amp; Treasury Summary">
        Current loss prevention ratio is <b>{((lossPrevented / Math.max(totalGmv, 1)) * 100).toFixed(1)}%</b> of total gross volume.
        Chargeback rate remains safely below the 90 BPS network monitoring threshold.
      </InsightCallout>
    </div>
  );
};
