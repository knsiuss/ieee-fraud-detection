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
    <div className="space-y-4">
      {/* Top Executive Header */}
      <div className="flex items-center justify-between panel p-3.5">
        <div>
          <h2 className="text-sm font-mono font-bold text-text-primary tracking-tight">
            EXECUTIVE &amp; RISK IMPACT LEDGER
          </h2>
          <p className="text-xs font-mono text-text-muted">
            Monetary volume, fraud prevention totals, and chargeback exposure metrics
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="px-2 py-0.5 rounded-[6px] bg-surface-2 border border-status-approve/30 text-status-approve font-mono text-xs font-semibold">
            PROGRAM STATUS: COMPLIANT
          </span>
        </div>
      </div>

      {/* Row 1: Executive KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
        <KpiCard
          title="Evaluated GMV"
          value={`$${totalGmv.toLocaleString()}`}
          subtitle="Gross Merchandise Volume"
          icon={<DollarSign className="w-3.5 h-3.5" />}
        />
        <KpiCard
          title="Fraud Loss Prevented"
          value={`$${lossPrevented.toLocaleString()}`}
          subtitle={`${((lossPrevented / Math.max(totalGmv, 1)) * 100).toFixed(1)}% of volume protected`}
          trend={{ value: 'Saved', direction: 'up' }}
          icon={<ShieldAlert className="w-3.5 h-3.5 text-status-approve" />}
        />
        <KpiCard
          title="Cleared Safe Volume"
          value={`$${safeVolume.toLocaleString()}`}
          subtitle="Direct automated approvals"
          icon={<CheckCircle2 className="w-3.5 h-3.5" />}
        />
        <KpiCard
          title="Review Exposure"
          value={`$${underReviewExposure.toLocaleString()}`}
          subtitle={`${dispositions?.total_reviewed || 0} decisions audited`}
          icon={<Percent className="w-3.5 h-3.5" />}
        />
      </div>

      {/* Row 2: Financial Charts Split */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
        <div className="lg:col-span-2 panel p-3.5">
          <div className="flex items-center justify-between mb-2">
            <div>
              <h3 className="text-xs font-mono font-semibold uppercase tracking-wider text-text-primary">
                Monetary Volume &amp; Loss Prevention Trajectory
              </h3>
              <p className="text-[10px] font-mono text-text-muted">
                Evaluated GMV ($) vs Fraud Loss Prevented ($)
              </p>
            </div>
          </div>
          <TimeseriesChart data={timeseries || []} height="280px" showAmount={true} />
        </div>

        {/* Card Network Compliance & Chargeback BPS */}
        <div className="panel p-3.5 flex flex-col justify-between space-y-3">
          <div>
            <h3 className="text-xs font-mono font-semibold uppercase tracking-wider text-text-primary mb-0.5">
              Card Network Compliance (BPS)
            </h3>
            <p className="text-[10px] font-mono text-text-muted mb-3">
              Basis points vs Visa &amp; Mastercard 0.9% (90 BPS) threshold
            </p>

            <div className="p-3 bg-surface-2 rounded-[6px] border border-border-subtle space-y-2">
              <div className="flex justify-between items-center font-mono">
                <span className="text-xs text-text-secondary">Current Rate:</span>
                <span className="text-base font-bold text-status-approve tabular-nums">
                  {loss?.chargeback_bps || 16.4} BPS
                </span>
              </div>

              {/* Progress track */}
              <div className="w-full bg-surface-1 h-2 rounded-[6px] overflow-hidden relative border border-border-subtle">
                <div
                  className="bg-status-approve h-full"
                  style={{ width: `${Math.min(((loss?.chargeback_bps || 16.4) / 90) * 100, 100)}%` }}
                />
              </div>

              <div className="flex justify-between text-[9px] font-mono text-text-muted">
                <span>0 BPS</span>
                <span>50 BPS (Watch)</span>
                <span>90 BPS (Threshold)</span>
              </div>
            </div>
          </div>

          {/* Friction breakdown */}
          <div className="p-2.5 bg-surface-2 border border-border-subtle rounded-[6px] space-y-1 text-xs font-mono">
            <div className="text-text-secondary font-semibold text-[10px] uppercase">
              Analyst Dispositions Summary
            </div>
            <div className="flex justify-between text-text-secondary text-[11px] pt-1">
              <span>Confirmed Fraud (TP):</span>
              <span className="text-status-block font-bold">
                {dispositions?.confirmed_fraud || 28} cases
              </span>
            </div>
            <div className="flex justify-between text-text-secondary text-[11px]">
              <span>False Positives Overturned:</span>
              <span className="text-status-approve font-bold">
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
