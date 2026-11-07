import React, { useState, useRef, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../../lib/api';
import { useLiveStore } from '../../stores/useLiveStore';
import { useSelectedTxStore } from '../../stores/useSelectedTxStore';
import type { DecisionItem } from '../../lib/types';
import { KpiCard } from '../../components/ui/KpiCard';
import { StatusBadge } from '../../components/ui/StatusBadge';
import { AuditSampledBadge } from '../../components/ui/AuditSampledBadge';
import { ScoreBar } from '../../components/ui/ScoreBar';
import { DataTable } from '../../components/ui/DataTable';
import { TimeseriesChart } from '../../components/charts/TimeseriesChart';
import { DistributionChart } from '../../components/charts/DistributionChart';
import { InsightCallout } from '../../components/ui/InsightCallout';
import { Play, Pause, Zap, Activity, Filter, RefreshCw, Square } from 'lucide-react';
import type { ColumnDef } from '@tanstack/react-table';

const chargebackTrend = (bps?: number | null) => {
  if (bps == null) return { value: 'No data', direction: 'neutral' as const };
  if (bps >= 90) return { value: 'Elevated', direction: 'down' as const };
  if (bps >= 50) return { value: 'Watch', direction: 'neutral' as const };
  return { value: 'Nominal', direction: 'up' as const };
};

const fmtMs = (value?: number | null) =>
  value == null ? '—' : value >= 1000 ? `${(value / 1000).toFixed(2)}s` : `${value.toFixed(0)}ms`;

export const LiveRadar: React.FC = () => {
  const [isSimulating, setIsSimulating] = useState(false);
  const [simSpeed, setSimSpeed] = useState<number>(1);
  const simIntervalRef = useRef<any>(null);

  const decisions = useLiveStore((s) => s.decisions);
  const isPaused = useLiveStore((s) => s.isPaused);
  const togglePause = useLiveStore((s) => s.togglePause);
  const filterDecision = useLiveStore((s) => s.filterDecision);
  const setFilterDecision = useLiveStore((s) => s.setFilterDecision);
  const searchQuery = useLiveStore((s) => s.searchQuery);
  const setSearchQuery = useLiveStore((s) => s.setSearchQuery);
  const rollingTps = useLiveStore((s) => s.rollingTps);
  const counts = useLiveStore((s) => s.counts);

  const openDrawer = useSelectedTxStore((s) => s.openDrawer);

  const { data: summary, refetch: refetchSummary } = useQuery({
    queryKey: ['metrics-summary'],
    queryFn: api.getMetricsSummary,
    refetchInterval: 5000,
  });

  const { data: timeseries } = useQuery({
    queryKey: ['metrics-timeseries'],
    queryFn: () => api.getMetricsTimeseries(30, 60),
    refetchInterval: 5000,
  });

  // Clean up timer on unmount
  useEffect(() => {
    return () => {
      if (simIntervalRef.current) {
        clearTimeout(simIntervalRef.current);
        simIntervalRef.current = null;
      }
    };
  }, []);

  // Simulator helper: triggers rapid transactions
  const handleToggleSimulation = () => {
    if (isSimulating) {
      if (simIntervalRef.current) {
        clearTimeout(simIntervalRef.current);
        simIntervalRef.current = null;
      }
      setIsSimulating(false);
      return;
    }

    setIsSimulating(true);
    const profiles: Array<'typical' | 'nonfraud' | 'fraud'> = ['typical', 'nonfraud', 'fraud', 'typical', 'typical', 'nonfraud'];

    const tick = async () => {
      const profile = profiles[Math.floor(Math.random() * profiles.length)];
      const amount = profile === 'fraud' ? 850 + Math.random() * 1200 : 25 + Math.random() * 200;
      try {
        await api.simulate({
          profile,
          amount: Math.round(amount * 100) / 100,
          card_brand: profile === 'fraud' ? 'discover' : (Math.random() > 0.5 ? 'visa' : 'mastercard'),
          billing_distance: profile === 'fraud' ? 1200 + Math.random() * 2000 : 12,
          card_match_count: profile === 'fraud' ? 12 + Math.floor(Math.random() * 15) : 1,
          purchase_frequency: profile === 'fraud' ? 25 + Math.floor(Math.random() * 40) : 1,
          days_since_activity: profile === 'fraud' ? 0 : 2,
        });
      } catch {
        // ignore
      }
      if (simIntervalRef.current !== null) {
        simIntervalRef.current = window.setTimeout(tick, 1000 / simSpeed);
      }
    };
    simIntervalRef.current = window.setTimeout(tick, 1000 / simSpeed);
  };

  // Filter decisions in memory
  const filteredDecisions = decisions.filter((d) => {
    if (filterDecision !== 'ALL' && d.decision !== filterDecision) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      return (
        d.transaction_id.toLowerCase().includes(q) ||
        d.decision.toLowerCase().includes(q) ||
        (d.action && d.action.toLowerCase().includes(q))
      );
    }
    return true;
  });

  const columns: ColumnDef<DecisionItem, any>[] = [
    {
      accessorKey: 'decision',
      header: 'Decision',
      cell: ({ row }) => (
        <div className="flex items-center gap-2">
          <StatusBadge status={row.original.decision} size="sm" />
          {row.original.audit_sampled && <AuditSampledBadge />}
        </div>
      ),
    },
    {
      accessorKey: 'score',
      header: 'Risk Score & Driver',
      cell: ({ row }) => {
        const firstReason = row.original.reason_codes?.[0];
        const topDriver = firstReason?.feature
          ? {
              label: firstReason.feature,
              direction: (firstReason.contribution && firstReason.contribution > 0 ? 'fraud' : 'safe') as 'fraud' | 'safe',
            }
          : undefined;

        return (
          <div className="w-52">
            <ScoreBar
              probability={row.original.score}
              topDriver={topDriver}
              showPercentage={true}
              compact={true}
            />
          </div>
        );
      },
    },
    {
      accessorKey: 'transaction_id',
      header: 'Transaction ID',
      cell: ({ row }) => (
        <span className="font-mono text-xs font-semibold text-text-primary">
          {row.original.transaction_id}
        </span>
      ),
    },
    {
      id: 'amount',
      header: 'Amount',
      cell: ({ row }) => {
        const amt = row.original.amount ?? row.original.input_features?.TransactionAmt;
        return (
          <span className="font-mono text-xs font-medium text-text-primary tabular-nums">
            {amt !== undefined ? `$${Number(amt).toFixed(2)}` : '—'}
          </span>
        );
      },
    },
    {
      accessorKey: 'action',
      header: 'Policy Route',
      cell: ({ row }) => (
        <span className="text-[11px] font-sans font-medium text-text-secondary bg-surface-2 px-2.5 py-0.5 rounded-full border border-border-subtle">
          {row.original.action || 'Default Policy'}
        </span>
      ),
    },
    {
      accessorKey: 'timestamp',
      header: 'Observed',
      cell: ({ row }) => (
        <span className="text-[11px] font-mono text-text-muted">
          {row.original.timestamp ? new Date(row.original.timestamp).toLocaleTimeString() : '—'}
        </span>
      ),
    },
    {
      id: 'actions',
      header: '',
      cell: ({ row }) => (
        <button
          onClick={(e) => {
            e.stopPropagation();
            openDrawer(row.original);
          }}
          className="btn-interactive px-3 py-1 bg-surface-2 hover:bg-surface-hover border border-border-subtle rounded-full text-xs text-text-primary font-sans font-medium"
        >
          Details →
        </button>
      ),
    },
  ];

  return (
    <div className="space-y-4">
      {/* Toolbar */}
      <div className="panel flex flex-wrap items-center justify-between gap-3 px-4 py-2.5">
        <div className="flex items-center gap-2.5">
          <span className="flex items-center gap-2 text-[12px] font-medium text-text-secondary">
            <span
              className={`h-1.5 w-1.5 rounded-full ${
                isPaused ? 'bg-status-review' : 'bg-status-approve'
              }`}
            />
            {isPaused ? 'Stream paused' : 'Live stream'}
            <span className="font-mono text-[11px] text-text-muted">· {rollingTps} TPS</span>
          </span>
          <button onClick={togglePause} className="control h-7 text-[11.5px]">
            {isPaused ? (
              <Play className="h-3 w-3 text-status-approve" />
            ) : (
              <Pause className="h-3 w-3 text-text-muted" />
            )}
            <span>{isPaused ? 'Resume' : 'Pause'}</span>
          </button>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <label className="text-[11.5px] text-text-muted">Simulate</label>
          <div className="control h-7 gap-1.5 py-0">
            <select
              value={simSpeed}
              onChange={(e) => setSimSpeed(Number(e.target.value))}
              disabled={isSimulating}
              className="cursor-pointer bg-transparent pr-1 text-[12px] font-medium text-text-primary outline-none disabled:cursor-not-allowed disabled:opacity-50"
            >
              <option value={1}>1 tx/s</option>
              <option value={3}>3 tx/s</option>
              <option value={8}>8 tx/s</option>
            </select>
          </div>

          <button
            onClick={handleToggleSimulation}
            className={`btn-interactive inline-flex h-7 items-center gap-1.5 rounded-lg border px-3 text-[11.5px] font-medium ${
              isSimulating
                ? 'border-status-block/40 bg-status-block/10 text-status-block'
                : 'border-border-subtle bg-surface-2 text-text-primary hover:bg-surface-hover'
            }`}
          >
            {isSimulating ? (
              <Square className="h-3 w-3" />
            ) : (
              <Zap className="h-3 w-3 text-status-review" />
            )}
            <span>{isSimulating ? 'Stop traffic' : 'Inject traffic'}</span>
          </button>

          <button
            onClick={() => refetchSummary()}
            className="control h-7 w-7 justify-center p-0"
            title="Refresh metrics"
            aria-label="Refresh metrics"
          >
            <RefreshCw className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>

      {/* KPI row */}
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
        <KpiCard
          title="Volume"
          value={(summary?.total_decisions || 0).toLocaleString()}
          subtitle={`$${((summary?.gmv_total || 0) / 1000).toFixed(1)}k GMV`}
          trend={{ value: `${rollingTps} TPS`, direction: 'neutral' }}
        />
        <KpiCard
          title="Approved"
          value={`${summary?.percentages.APPROVE || 0}%`}
          subtitle={`${(summary?.counts.APPROVE || 0).toLocaleString()} transactions`}
          trend={{ value: `${counts.APPROVE} live`, direction: 'up' }}
        />
        <KpiCard
          title="Review"
          value={`${summary?.percentages.MANUAL_REVIEW || 0}%`}
          subtitle={`${(summary?.counts.MANUAL_REVIEW || 0).toLocaleString()} in queue`}
          trend={{ value: `${counts.MANUAL_REVIEW} live`, direction: 'neutral' }}
        />
        <KpiCard
          title="Declined"
          value={`${summary?.percentages.DECLINE || 0}%`}
          subtitle={`$${((summary?.loss_prevented || 0) / 1000).toFixed(1)}k prevented`}
          trend={{ value: `${counts.DECLINE} live`, direction: 'down' }}
        />
        <KpiCard
          title="Latency"
          value={fmtMs(summary?.latency.p95_ms)}
          subtitle={`p50 ${fmtMs(summary?.latency.p50_ms)} · p99 ${fmtMs(summary?.latency.p99_ms)} · n=${summary?.latency.samples ?? 0}`}
        />
        <KpiCard
          title="Chargeback"
          value={summary?.chargeback_bps != null ? `${summary.chargeback_bps}` : '—'}
          subtitle="Visa limit 90 BPS"
          trend={chargebackTrend(summary?.chargeback_bps)}
        />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 gap-3.5 lg:grid-cols-3">
        <section className="panel lg:col-span-2">
          <div className="panel-header">
            <div className="flex items-center gap-2">
              <Activity className="h-3.5 w-3.5 text-text-muted" />
              <h3 className="section-title">Transaction velocity &amp; decision stream</h3>
            </div>
            <span className="meta-text">30m rolling · 60s windows</span>
          </div>
          <div className="panel-body pt-3">
            <TimeseriesChart data={timeseries || []} height="244px" />
          </div>
        </section>

        <section className="panel flex flex-col">
          <div className="panel-header">
            <h3 className="section-title">Score distribution</h3>
            <span className="meta-text">10-bin histogram</span>
          </div>
          <div className="panel-body flex-1 pt-3">
            <DistributionChart scores={decisions.map((d) => d.score)} height="200px" />
          </div>
          <div className="flex items-center justify-between border-t border-border-subtle px-4 py-2.5 text-[11px]">
            <span className="text-status-approve">Approve &lt; 0.20</span>
            <span className="text-status-review">Review 0.20–0.80</span>
            <span className="text-status-block">Decline &gt; 0.80</span>
          </div>
        </section>
      </div>

      {/* Decision stream */}
      <section className="panel overflow-hidden">
        <div className="panel-header flex-wrap gap-3">
          <div>
            <h3 className="section-title">Real-time decision stream</h3>
            <p className="meta-text mt-0.5">In-memory buffer · {decisions.length} events</p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <div className="control h-8 gap-2 py-0">
              <Filter className="h-3.5 w-3.5 text-text-muted" />
              <select
                value={filterDecision}
                onChange={(e) => setFilterDecision(e.target.value as any)}
                className="cursor-pointer bg-transparent pr-1 text-[12px] font-medium text-text-primary outline-none"
              >
                <option value="ALL">All decisions</option>
                <option value="APPROVE">Approve only</option>
                <option value="MANUAL_REVIEW">Review only</option>
                <option value="DECLINE">Decline only</option>
              </select>
            </div>

            <input
              type="text"
              placeholder="Search transaction or action"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="h-8 w-56 rounded-lg border border-border-subtle bg-surface-2 px-3 text-[12px] text-text-primary placeholder:text-text-muted focus:border-apple-blue focus:outline-none"
            />
          </div>
        </div>

        <DataTable
          bare
          columns={columns}
          data={filteredDecisions}
          onRowClick={(row) => openDrawer(row)}
          idAccessor={(row) => row.transaction_id}
          emptyMessage="No decisions in buffer yet. Start the traffic simulator or score a transaction."
        />
      </section>

      <InsightCallout title="Operations note">
        Decision latency p95 is <b>{fmtMs(summary?.latency.p95_ms)}</b> across{' '}
        <b>{summary?.latency.samples ?? 0}</b> measured decisions in the last 15 minutes.
        Auto-approval rate is <b>{summary?.percentages.APPROVE || 0}%</b>, with an estimated{' '}
        <b>${((summary?.loss_prevented || 0) / 1000).toFixed(1)}k</b> in prevented fraud losses.
      </InsightCallout>
    </div>
  );
};
