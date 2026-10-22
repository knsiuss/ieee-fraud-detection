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

  const totalGmv = loss?.total_gmv ?? summary?.gmv_total ?? null;
  const lossPrevented = loss?.loss_prevented ?? summary?.loss_prevented ?? null;
  const safeVolume =
    loss?.cleared_safe_volume ?? (totalGmv != null && lossPrevented != null ? totalGmv - lossPrevented : null);
  const underReviewExposure = loss?.under_review_exposure ?? null;
  const chargeback = loss?.chargeback_bps ?? null;
  const compliance =
    chargeback == null
      ? { label: 'Awaiting labelled data', className: 'border-status-review/30 bg-status-review/10 text-status-review' }
      : chargeback < 50
        ? { label: 'Program Status: Compliant', className: 'border-status-approve/30 bg-status-approve/12 text-status-approve' }
        : chargeback < 90
          ? { label: 'Program Status: Watch', className: 'border-status-review/30 bg-status-review/10 text-status-review' }
          : { label: 'Program Status: At Risk', className: 'border-status-block/30 bg-status-block/10 text-status-block' };
  const money = (value: number | null) =>
    value == null ? '—' : `$${Math.round(value).toLocaleString()}`;
  const protectionRatio =
    totalGmv != null && lossPrevented != null && totalGmv > 0
      ? (lossPrevented / totalGmv) * 100
      : null;

  return (
    <div className="space-y-5">
      {/* Top Executive Header */}
      <div className="flex items-center justify-between panel p-5 rounded-xl">
        <div>
          <h2 className="text-[15px] font-semibold tracking-tight text-text-primary">
            Executive &amp; Risk Impact Ledger
          </h2>
          <p className="text-xs font-sans text-text-muted mt-0.5">
            Monetary volume, fraud prevention totals, and chargeback exposure metrics
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span
            className={`rounded-full border px-3 py-1 font-sans text-xs font-medium ${compliance.className}`}
          >
            {compliance.label}
          </span>
        </div>
      </div>

      {/* Row 1: Executive KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3.5">
        <KpiCard
          title="Evaluated GMV"
          value={money(totalGmv)}
          subtitle="Gross Merchandise Volume"
          icon={<DollarSign className="w-4 h-4 text-apple-blue" />}
        />
        <KpiCard
          title="Fraud Loss Prevented"
          value={money(lossPrevented)}
          subtitle={
            protectionRatio != null
              ? `${protectionRatio.toFixed(1)}% of volume protected`
              : 'Awaiting volume data'
          }
          trend={{ value: 'Saved', direction: 'up' }}
          icon={<ShieldAlert className="w-4 h-4 text-status-approve" />}
        />
        <KpiCard
          title="Cleared Safe Volume"
          value={money(safeVolume)}
          subtitle="Direct automated approvals"
          icon={<CheckCircle2 className="w-4 h-4 text-apple-indigo" />}
        />
        <KpiCard
          title="Review Exposure"
          value={money(underReviewExposure)}
          subtitle={`${dispositions?.total_reviewed ?? 0} cases reviewed`}
          icon={<Percent className="w-4 h-4 text-status-review" />}
        />
      </div>

      {/* Row 2: Financial Charts Split */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-3.5">
        <div className="lg:col-span-2 panel p-5 rounded-xl">
          <div className="flex items-center justify-between mb-3">
            <div>
              <h3 className="text-[13px] font-semibold text-text-primary">
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
        <div className="panel p-5 rounded-xl flex flex-col justify-between space-y-4">
          <div>
            <h3 className="mb-0.5 text-[13px] font-semibold text-text-primary">
              Card Network Compliance (BPS)
            </h3>
            <p className="text-[11px] font-sans text-text-muted mb-4">
              Basis points vs Visa &amp; Mastercard 0.9% (90 BPS) threshold
            </p>

            <div className="p-4 bg-surface-2 rounded-xl border border-border-subtle space-y-3">
              <div className="flex justify-between items-center font-sans">
                <span className="text-xs text-text-secondary font-medium">Current Rate:</span>
                <span className="text-lg font-bold font-mono text-status-approve tabular-nums">
                  {loss?.chargeback_bps != null ? `${loss.chargeback_bps} BPS` : '—'}
                </span>
              </div>

              {/* Progress pill track */}
              <div className="w-full bg-surface-1 h-2.5 rounded-full overflow-hidden relative border border-border-subtle p-0.5">
                <div
                  className="bg-status-approve h-full rounded-full transition-all duration-300"
                  style={{ width: `${Math.min(((loss?.chargeback_bps ?? 0) / 90) * 100, 100)}%` }}
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
          <div className="p-4 bg-surface-2 border border-border-subtle rounded-xl space-y-2 text-xs font-sans">
            <div className="text-[11px] font-medium text-text-muted">
              Analyst Dispositions Summary
            </div>
            <div className="flex justify-between text-text-secondary text-xs pt-1">
              <span>Confirmed Fraud (TP):</span>
              <span className="text-status-block font-bold font-mono">
                {dispositions?.confirmed_fraud ?? 0} cases
              </span>
            </div>
            <div className="flex justify-between text-text-secondary text-xs">
              <span>False Positives Overturned:</span>
              <span className="text-status-approve font-bold font-mono">
                {dispositions?.false_positives ?? 0} cases
              </span>
            </div>
          </div>
        </div>
      </div>

      <InsightCallout title="Credit Risk &amp; Treasury Summary">
        {totalGmv != null && lossPrevented != null ? (
          <>
            Current loss prevention ratio is{' '}
            <b>{((lossPrevented / Math.max(totalGmv, 1)) * 100).toFixed(1)}%</b> of total gross
            volume.{' '}
          </>
        ) : (
          <>No volume data yet for this workspace. </>
        )}
        {chargeback == null
          ? 'Chargeback BPS is not measurable until at least 20 approved transactions carry a labelled outcome; no compliance claim is made.'
          : chargeback < 50
            ? `Chargeback rate (${chargeback} BPS) is below the 50 BPS watch band.`
            : chargeback < 90
              ? `Chargeback rate (${chargeback} BPS) is in the 50–90 BPS watch band.`
              : `Chargeback rate (${chargeback} BPS) exceeds the 90 BPS network threshold.`}
      </InsightCallout>
    </div>
  );
};
