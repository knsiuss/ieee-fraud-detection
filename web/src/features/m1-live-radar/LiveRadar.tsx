import React, { useState } from 'react';
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
import { Play, Pause, Zap, Activity, Filter, RefreshCw } from 'lucide-react';
import type { ColumnDef } from '@tanstack/react-table';

export const LiveRadar: React.FC = () => {
  const [isSimulating, setIsSimulating] = useState(false);
  const [simSpeed, setSimSpeed] = useState<number>(1);

  const {
    decisions,
    isPaused,
    togglePause,
    filterDecision,
    setFilterDecision,
    searchQuery,
    setSearchQuery,
    rollingTps,
    counts,
  } = useLiveStore();

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

  // Simulator helper: triggers rapid transactions
  const handleToggleSimulation = () => {
    if (isSimulating) {
      setIsSimulating(false);
      return;
    }

    setIsSimulating(true);
    let count = 0;
    const profiles: Array<'typical' | 'nonfraud' | 'fraud'> = ['typical', 'nonfraud', 'fraud', 'typical'];

    const interval = setInterval(async () => {
      if (count >= 30) {
        clearInterval(interval);
        setIsSimulating(false);
        return;
      }
      count++;
      const profile = profiles[Math.floor(Math.random() * profiles.length)];
      const amount = profile === 'fraud' ? 850 + Math.random() * 1200 : 25 + Math.random() * 200;
      try {
        await api.simulate({
          profile,
          amount: Math.round(amount * 100) / 100,
          card_brand: profile === 'fraud' ? 'discover' : 'visa',
          billing_distance: profile === 'fraud' ? 450 : 12,
        });
      } catch {
        // ignore
      }
    }, 1000 / simSpeed);
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
        <div className="flex items-center gap-1.5">
          <StatusBadge status={row.original.decision} size="sm" />
          {row.original.audit_sampled && <AuditSampledBadge />}
        </div>
      ),
    },
    {
      accessorKey: 'timestamp',
      header: 'Time (UTC)',
      cell: ({ row }) => {
        try {
          const t = new Date(row.original.timestamp);
          return `${t.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}.${String(
            t.getMilliseconds()
          ).padStart(3, '0')}`;
        } catch {
          return row.original.timestamp;
        }
      },
    },
    {
      accessorKey: 'transaction_id',
      header: 'Transaction ID',
      cell: ({ row }) => (
        <span className="font-bold text-text-primary">
          #{row.original.transaction_id.slice(-8)}
        </span>
      ),
    },
    {
      accessorKey: 'score',
      header: 'Risk Probability Track',
      cell: ({ row }) => (
        <div className="w-44">
          <ScoreBar probability={row.original.score} compact={true} />
        </div>
      ),
    },
    {
      accessorKey: 'action',
      header: 'Policy Action',
      cell: ({ row }) => (
        <span className="text-text-muted text-[11px] font-mono">
          {row.original.action || 'Default Policy'}
        </span>
      ),
    },
    {
      id: 'actions',
      header: 'Inspect',
      cell: ({ row }) => (
        <button
          onClick={(e) => {
            e.stopPropagation();
            openDrawer(row.original);
          }}
          className="btn-interactive px-2 py-0.5 bg-surface-2 hover:bg-surface-hover border border-border-subtle rounded-[2px] text-[11px] text-text-primary font-mono"
        >
          Details →
        </button>
      ),
    },
  ];

  return (
    <div className="space-y-4">
      {/* Top Real-time Control Strip */}
      <div className="flex flex-wrap items-center justify-between gap-3 panel p-3">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 px-2.5 py-1 bg-surface-2 rounded-[2px] border border-border-subtle font-mono text-xs">
            <span className="w-2 h-2 rounded-full bg-status-approve" />
            <span className="text-text-primary font-medium">LIVE DECISION STREAM</span>
            <span className="text-text-muted text-[11px]">({rollingTps} TPS)</span>
          </div>

          <button
            onClick={togglePause}
            className="btn-interactive inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-mono rounded-[2px] border border-border-subtle bg-surface-2 text-text-secondary hover:text-text-primary hover:bg-surface-hover"
          >
            {isPaused ? <Play className="w-3 h-3" /> : <Pause className="w-3 h-3" />}
            <span>{isPaused ? 'Resume Stream' : 'Pause Stream'}</span>
          </button>
        </div>

        {/* Traffic Simulation Controls */}
        <div className="flex items-center gap-2">
          <span className="text-xs font-mono text-text-muted">Simulate:</span>
          <select
            value={simSpeed}
            onChange={(e) => setSimSpeed(Number(e.target.value))}
            className="bg-surface-2 border border-border-subtle text-text-primary text-xs font-mono px-2 py-1 rounded-[2px] focus:outline-none"
          >
            <option value={1}>1 tx/s</option>
            <option value={3}>3 tx/s</option>
            <option value={8}>8 tx/s</option>
          </select>

          <button
            onClick={handleToggleSimulation}
            className={`btn-interactive inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-mono rounded-[2px] border ${
              isSimulating
                ? 'bg-surface-hover text-text-primary border-border-muted font-bold'
                : 'bg-surface-2 text-text-primary border-border-subtle hover:bg-surface-hover'
            }`}
          >
            <Zap className="w-3 h-3 text-text-muted" />
            <span>{isSimulating ? 'Injecting...' : 'Inject Traffic'}</span>
          </button>

          <button
            onClick={() => refetchSummary()}
            className="btn-interactive p-1 text-text-muted hover:text-text-primary hover:bg-surface-hover rounded-[2px] border border-border-subtle"
            title="Refresh metrics"
            aria-label="Refresh metrics"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Row 1: KPI Cards Grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        <KpiCard
          title="Total Volume"
          value={(summary?.total_decisions || 0).toLocaleString()}
          subtitle={`$${((summary?.gmv_total || 0) / 1000).toFixed(1)}k GMV`}
          trend={{ value: `${rollingTps} TPS`, direction: 'up' }}
        />
        <KpiCard
          title="Auto-Approved"
          value={`${summary?.percentages.APPROVE || 0}%`}
          subtitle={`${(summary?.counts.APPROVE || 0).toLocaleString()} tx`}
          trend={{ value: `${counts.APPROVE} live`, direction: 'neutral' }}
        />
        <KpiCard
          title="Manual Review"
          value={`${summary?.percentages.MANUAL_REVIEW || 0}%`}
          subtitle={`${(summary?.counts.MANUAL_REVIEW || 0).toLocaleString()} in queue`}
          trend={{ value: `${counts.MANUAL_REVIEW} live`, direction: 'neutral' }}
        />
        <KpiCard
          title="Declined (Fraud)"
          value={`${summary?.percentages.DECLINE || 0}%`}
          subtitle={`$${((summary?.loss_prevented || 0) / 1000).toFixed(1)}k Prevented`}
          trend={{ value: `${counts.DECLINE} live`, direction: 'down' }}
        />
        <KpiCard
          title="Inference Latency"
          value={`${summary?.latency.p95_ms || 14.2}ms`}
          subtitle={`p50: ${summary?.latency.p50_ms || 7.8}ms | p99: ${summary?.latency.p99_ms || 23.5}ms`}
        />
        <KpiCard
          title="Chargeback BPS"
          value={`${summary?.chargeback_bps || 16.4}`}
          subtitle="Visa Limit: 90 BPS"
          trend={{ value: 'Nominal', direction: 'up' }}
        />
      </div>

      {/* Row 2: Charts Split */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
        <div className="lg:col-span-2 panel p-3.5">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-1.5">
              <Activity className="w-3.5 h-3.5 text-text-muted" />
              <h3 className="text-xs font-mono font-semibold uppercase tracking-wider text-text-primary">
                Transaction Velocity &amp; Policy Decision Stream
              </h3>
            </div>
            <span className="text-[10px] font-mono text-text-muted">30m Rolling (60s Windows)</span>
          </div>
          <TimeseriesChart data={timeseries || []} height="260px" />
        </div>

        <div className="panel p-3.5 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-xs font-mono font-semibold uppercase tracking-wider text-text-primary">
                Score Distribution
              </h3>
              <span className="text-[10px] font-mono text-text-muted">10-Bin Histogram</span>
            </div>
            <DistributionChart
              scores={decisions.map((d) => d.score)}
              height="220px"
            />
          </div>
          <div className="text-[10px] font-mono text-text-muted flex justify-between pt-2 border-t border-border-subtle">
            <span>Approve &lt; 0.20</span>
            <span>Review 0.20–0.80</span>
            <span>Decline &gt; 0.80</span>
          </div>
        </div>
      </div>

      {/* Row 3: Live Feed Table + Search & Filter */}
      <div className="panel p-3.5 space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h3 className="text-xs font-mono font-semibold uppercase tracking-wider text-text-primary">
              Real-Time Decision Stream
            </h3>
            <p className="text-[11px] font-mono text-text-muted">
              In-memory ring buffer ({decisions.length} events buffered)
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <div className="flex items-center gap-1.5 bg-surface-2 border border-border-subtle px-2 py-1 rounded-[2px] text-xs font-mono">
              <Filter className="w-3 h-3 text-text-muted" />
              <select
                value={filterDecision}
                onChange={(e) => setFilterDecision(e.target.value as any)}
                className="bg-transparent text-text-primary focus:outline-none"
              >
                <option value="ALL">All Decisions</option>
                <option value="APPROVE">Approve Only</option>
                <option value="MANUAL_REVIEW">Review Only</option>
                <option value="DECLINE">Decline Only</option>
              </select>
            </div>

            <input
              type="text"
              placeholder="Search TxID or Action..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="bg-surface-2 border border-border-subtle text-text-primary text-xs font-mono px-2.5 py-1 rounded-[2px] w-48 placeholder:text-text-muted focus:outline-none focus:border-border-muted"
            />
          </div>
        </div>

        <DataTable
          columns={columns}
          data={filteredDecisions}
          onRowClick={(row) => openDrawer(row)}
          idAccessor={(row) => row.transaction_id}
          emptyMessage="No decisions in buffer yet. Start traffic simulator or execute scoring requests."
        />
      </div>

      {/* Key Insight */}
      <InsightCallout title="SOC Operations Note">
        Pipeline latency is operating within target SLAs (<b>{summary?.latency.p95_ms || 14.2}ms p95</b>).
        Auto-approval rate is <b>{summary?.percentages.APPROVE || 0}%</b>, with an estimated{' '}
        <b>${((summary?.loss_prevented || 0) / 1000).toFixed(1)}k</b> in prevented fraud losses.
      </InsightCallout>
    </div>
  );
};
