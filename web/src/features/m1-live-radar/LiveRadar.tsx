import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../../lib/api';
import { useLiveStore } from '../../stores/useLiveStore';
import { useSelectedTxStore } from '../../stores/useSelectedTxStore';
import type { DecisionItem } from '../../lib/types';
import { KpiCard } from '../../components/ui/KpiCard';
import { StatusBadge } from '../../components/ui/StatusBadge';
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
      cell: ({ row }) => <StatusBadge status={row.original.decision} size="sm" />,
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
        <span className="font-bold text-text-primary hover:text-accent-teal transition-colors">
          #{row.original.transaction_id.slice(-8)}
        </span>
      ),
    },
    {
      accessorKey: 'score',
      header: 'Risk Score',
      cell: ({ row }) => {
        const score = row.original.score;
        const color = score > 0.8 ? 'text-status-block' : score > 0.2 ? 'text-status-review' : 'text-status-approve';
        return (
          <div className="flex items-center gap-2">
            <div className="w-12 bg-surface-hover h-1.5 rounded-full overflow-hidden">
              <div
                className={`h-full ${
                  score > 0.8 ? 'bg-status-block' : score > 0.2 ? 'bg-status-review' : 'bg-status-approve'
                }`}
                style={{ width: `${Math.round(score * 100)}%` }}
              />
            </div>
            <span className={`font-bold ${color}`}>{(score * 100).toFixed(1)}%</span>
          </div>
        );
      },
    },
    {
      accessorKey: 'action',
      header: 'Policy Action',
      cell: ({ row }) => (
        <span className="text-text-muted text-[11px] uppercase">{row.original.action || 'Standard Policy'}</span>
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
          className="px-2 py-1 bg-surface-2 hover:bg-surface-hover border border-border-subtle rounded text-[10px] text-accent-sky font-semibold transition-colors"
        >
          Forensics →
        </button>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      {/* Top Real-time Control Strip */}
      <div className="flex flex-wrap items-center justify-between gap-4 bg-surface-1 border border-border-subtle p-3.5 rounded-lg">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 px-2.5 py-1 bg-surface-2 rounded-md border border-border-subtle font-mono text-xs">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-status-approve opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-status-approve"></span>
            </span>
            <span className="text-text-primary font-medium">LIVE STREAM RADAR</span>
            <span className="text-text-muted text-[11px]">({rollingTps} TPS)</span>
          </div>

          <button
            onClick={togglePause}
            className={`inline-flex items-center gap-1.5 px-3 py-1 text-xs font-mono rounded border transition-colors ${
              isPaused
                ? 'bg-status-review/15 text-status-review border-status-review/30 hover:bg-status-review/25'
                : 'bg-surface-2 text-text-secondary border-border-subtle hover:text-text-primary hover:bg-surface-hover'
            }`}
          >
            {isPaused ? <Play className="w-3.5 h-3.5" /> : <Pause className="w-3.5 h-3.5" />}
            <span>{isPaused ? 'Resume Stream' : 'Pause Stream'}</span>
          </button>
        </div>

        {/* Traffic Simulation Controls */}
        <div className="flex items-center gap-2">
          <span className="text-xs font-mono text-text-muted">Simulate Load:</span>
          <select
            value={simSpeed}
            onChange={(e) => setSimSpeed(Number(e.target.value))}
            className="bg-surface-2 border border-border-subtle text-text-primary text-xs font-mono px-2 py-1 rounded"
          >
            <option value={1}>1x (1 tx/s)</option>
            <option value={3}>3x (3 tx/s)</option>
            <option value={8}>8x Burst (8 tx/s)</option>
          </select>

          <button
            onClick={handleToggleSimulation}
            className={`inline-flex items-center gap-1.5 px-3 py-1 text-xs font-mono rounded border transition-all ${
              isSimulating
                ? 'bg-accent-teal text-white border-accent-teal shadow-xs'
                : 'bg-surface-2 text-accent-teal border-accent-teal/30 hover:bg-accent-teal/10'
            }`}
          >
            <Zap className="w-3.5 h-3.5" />
            <span>{isSimulating ? 'Injecting Traffic...' : 'Inject Simulated Traffic'}</span>
          </button>

          <button
            onClick={() => refetchSummary()}
            className="p-1 text-text-muted hover:text-text-primary hover:bg-surface-hover rounded border border-border-subtle"
            title="Refresh metrics"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Row 1: KPI Cards Grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3.5">
        <KpiCard
          title="Total Volume"
          value={(summary?.total_decisions || 0).toLocaleString()}
          subtitle={`$${((summary?.gmv_total || 0) / 1000).toFixed(1)}k GMV Evaluated`}
          trend={{ value: `${rollingTps} TPS`, direction: 'up' }}
          accent="cyan"
          pulse={!isPaused}
        />
        <KpiCard
          title="Auto-Approved"
          value={`${summary?.percentages.APPROVE || 0}%`}
          subtitle={`${(summary?.counts.APPROVE || 0).toLocaleString()} transactions`}
          trend={{ value: `${counts.APPROVE} live`, direction: 'neutral' }}
          accent="emerald"
        />
        <KpiCard
          title="Manual Review"
          value={`${summary?.percentages.MANUAL_REVIEW || 0}%`}
          subtitle={`${(summary?.counts.MANUAL_REVIEW || 0).toLocaleString()} in queue`}
          trend={{ value: `${counts.MANUAL_REVIEW} live`, direction: 'neutral' }}
          accent="amber"
        />
        <KpiCard
          title="Declined (Fraud)"
          value={`${summary?.percentages.DECLINE || 0}%`}
          subtitle={`$${((summary?.loss_prevented || 0) / 1000).toFixed(1)}k Loss Prevented`}
          trend={{ value: `${counts.DECLINE} live`, direction: 'down' }}
          accent="crimson"
        />
        <KpiCard
          title="Inference Latency"
          value={`${summary?.latency.p95_ms || 14.2}ms`}
          subtitle={`p50: ${summary?.latency.p50_ms || 7.8}ms | p99: ${summary?.latency.p99_ms || 23.5}ms`}
          accent="teal"
        />
        <KpiCard
          title="Chargeback BPS"
          value={`${summary?.chargeback_bps || 16.4}`}
          subtitle="Visa/MC Threshold: 90 BPS"
          trend={{ value: 'Nominal', direction: 'up' }}
          accent="teal"
        />
      </div>

      {/* Row 2: Charts Split (Velocity Area Chart + Risk Distribution) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2 bg-surface-1 border border-border-subtle rounded-lg p-4">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <Activity className="w-4 h-4 text-accent-cyan" />
              <h3 className="text-xs font-semibold uppercase tracking-wider text-text-primary">
                Real-Time Transaction Velocity &amp; Anomaly Spike Stream
              </h3>
            </div>
            <span className="text-[11px] font-mono text-text-muted">30m Rolling Window (60s Buckets)</span>
          </div>
          <TimeseriesChart data={timeseries || []} height="280px" />
        </div>

        <div className="bg-surface-1 border border-border-subtle rounded-lg p-4 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-text-primary">
                Live Score Distribution
              </h3>
              <span className="text-[10px] font-mono text-text-muted">Probability Histogram</span>
            </div>
            <DistributionChart
              scores={decisions.map((d) => d.score)}
              height="240px"
            />
          </div>
          <div className="text-[11px] font-mono text-text-muted flex justify-between pt-2 border-t border-border-subtle">
            <span className="text-status-approve">● Safe &lt; 0.20</span>
            <span className="text-status-review">● Review 0.20–0.80</span>
            <span className="text-status-block">● Decline &gt; 0.80</span>
          </div>
        </div>
      </div>

      {/* Row 3: Live Feed Table + Search & Filter */}
      <div className="bg-surface-1 border border-border-subtle rounded-lg p-4 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h3 className="text-xs font-semibold uppercase tracking-wider text-text-primary">
              Real-Time Decision Stream
            </h3>
            <p className="text-[11px] font-mono text-text-muted">
              Auto-updating WebSocket/SSE buffer ({decisions.length} events buffered in memory)
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <div className="flex items-center gap-1 bg-surface-2 border border-border-subtle px-2 py-1 rounded text-xs font-mono">
              <Filter className="w-3.5 h-3.5 text-text-muted" />
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
              className="bg-surface-2 border border-border-subtle text-text-primary text-xs font-mono px-3 py-1 rounded w-48 placeholder:text-text-muted focus:outline-none focus:border-accent-teal"
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

      {/* Key Insight for Credit & SOC Analysts */}
      <InsightCallout title="SOC & Fraud Analyst Operations Insight" variant="tip">
        Real-time pipeline is processing traffic at optimal latency (<b>{summary?.latency.p95_ms || 14.2}ms p95</b>).
        Current automatic approval rate is healthy at <b>{summary?.percentages.APPROVE || 0}%</b>, preventing an estimated{' '}
        <b>${((summary?.loss_prevented || 0) / 1000).toFixed(1)}k</b> in unauthorized chargebacks while keeping manual review queue within SLA limits.
      </InsightCallout>
    </div>
  );
};
