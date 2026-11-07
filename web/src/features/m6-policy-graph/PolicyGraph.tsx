import React, { useCallback, useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../../lib/api';
import { FraudRingGraph } from '../../components/charts/FraudRingGraph';
import { InsightCallout } from '../../components/ui/InsightCallout';
import { Sliders, GitMerge, Network } from 'lucide-react';

export const PolicyGraph: React.FC = () => {
  const [lowerThreshold, setLowerThreshold] = useState<number>(0.2);
  const [upperThreshold, setUpperThreshold] = useState<number>(0.8);
  const [selectedNode, setSelectedNode] = useState<{ id: string; type: string } | null>(null);

  const { data: policy } = useQuery({ queryKey: ['policy'], queryFn: api.getPolicy });
  const { data: bandit } = useQuery({
    queryKey: ['bandit-status'],
    queryFn: api.getBanditStatus,
  });

  useEffect(() => {
    if (!policy) return;
    setLowerThreshold(policy.thresholds.review_above);
    setUpperThreshold(policy.thresholds.decline_above);
  }, [policy]);

  const costMode = policy?.kind === 'cost';
  const handleNodeClick = useCallback((id: string, type: string) => {
    setSelectedNode({ id, type });
  }, []);

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between panel p-5 rounded-xl">
        <div>
          <h2 className="text-[15px] font-semibold tracking-tight text-text-primary">
            Decision Policy Engine &amp; Fraud Network Graph
          </h2>
          <p className="text-xs font-sans text-text-muted mt-0.5">
            Cutoffs, adaptive-layer status and linked-entity topology for the served decision policy
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Left Policy Config (5 Cols) */}
        <div className="lg:col-span-5 space-y-4">
          <div className="panel p-5 space-y-4 rounded-xl">
            <div className="flex items-center gap-2 border-b border-border-subtle pb-3">
              <Sliders className="w-4 h-4 text-apple-blue" />
              <h3 className="text-[13px] font-semibold text-text-primary">
                Decision Cutoffs ({policy ? `policy ${policy.version}` : 'loading…'})
              </h3>
            </div>

            <div className="space-y-4 font-sans text-xs">
              {/* Lower Threshold */}
              <div>
                <div className="flex justify-between mb-1.5 font-medium">
                  <span className="text-text-secondary">Auto-Approve Cutoff:</span>
                  <span className="text-status-approve font-bold font-mono tabular-nums">{lowerThreshold.toFixed(2)}</span>
                </div>
                <input
                  type="range"
                  min="0.05"
                  max="0.4"
                  step="0.01"
                  value={lowerThreshold}
                  onChange={(e) => setLowerThreshold(Math.min(Number(e.target.value), upperThreshold - 0.01))}
                  className="w-full cursor-pointer accent-status-approve"
                />
                <span className="mt-1 block text-[11px] text-text-muted">
                  Scores &lt; {lowerThreshold.toFixed(2)} are approved automatically.
                  {costMode ? ' Cost mode uses expected-cost argmin, not this cutoff.' : ''}
                </span>
              </div>

              {/* Upper Threshold */}
              <div>
                <div className="flex justify-between mb-1.5 font-medium">
                  <span className="text-text-secondary">Auto-Decline Cutoff:</span>
                  <span className="text-status-block font-bold font-mono tabular-nums">{upperThreshold.toFixed(2)}</span>
                </div>
                <input
                  type="range"
                  min="0.3"
                  max="0.95"
                  step="0.01"
                  value={upperThreshold}
                  onChange={(e) => setUpperThreshold(Math.max(Number(e.target.value), lowerThreshold + 0.01))}
                  className="w-full cursor-pointer accent-status-block"
                />
                <span className="mt-1 block text-[11px] text-text-muted">
                  Scores &ge; {upperThreshold.toFixed(2)} are blocked instantly.
                </span>
              </div>

              <p className="text-[11px] leading-relaxed text-text-muted">
                Thresholds are server-configured via <code>DECISION_REVIEW_ABOVE</code> /{' '}
                <code>DECISION_DECLINE_ABOVE</code>; the sliders preview a policy change and do
                not mutate the live service.
              </p>

              {/* Threshold Visualizer Band */}
              <div className="p-4 bg-surface-2 rounded-xl border border-border-subtle space-y-2">
                <div className="text-xs font-medium text-text-secondary">Decision Spectrum:</div>
                <div className="h-4 w-full rounded-full overflow-hidden flex text-[10px] font-bold text-white text-center leading-4 p-0.5 bg-surface-1 border border-border-subtle">
                  <div
                    style={{ width: `${lowerThreshold * 100}%` }}
                    className="bg-status-approve rounded-l-full"
                  >
                    APPROVE
                  </div>
                  <div
                    style={{ width: `${(upperThreshold - lowerThreshold) * 100}%` }}
                    className="bg-status-review"
                  >
                    REVIEW
                  </div>
                  <div
                    style={{ width: `${(1 - upperThreshold) * 100}%` }}
                    className="bg-status-block rounded-r-full"
                  >
                    DECLINE
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Adaptive Contextual Bandit Layer */}
          <div className="panel p-5 space-y-3 font-sans text-xs rounded-xl">
            <div className="flex items-center gap-2 border-b border-border-subtle pb-3">
              <GitMerge className="w-4 h-4 text-apple-indigo" />
              <h3 className="text-[13px] font-semibold text-text-primary">
                Adaptive Contextual Bandit Telemetry
              </h3>
            </div>

            <div className="space-y-2.5 text-text-secondary">
              <div className="flex justify-between">
                <span>Adaptive layer:</span>
                <span
                  className={`rounded-full border px-2 py-0.5 text-[10px] font-medium ${
                    bandit?.enabled
                      ? 'border-status-approve/30 bg-status-approve/12 text-status-approve'
                      : 'border-border-subtle bg-surface-2 text-text-muted'
                  }`}
                >
                  {bandit?.enabled ? 'Enabled' : 'Disabled (FRAUD_BANDIT_ENABLED=0)'}
                </span>
              </div>
              <div className="flex justify-between">
                <span>Checkpoint:</span>
                <span className="font-mono font-medium text-text-primary">
                  {bandit?.checkpoint_version ?? 'none'}
                </span>
              </div>
              <div className="flex justify-between">
                <span>Rewarded events:</span>
                <span className="font-mono font-medium text-text-primary">
                  {bandit?.summary.n ?? 0}
                </span>
              </div>
              <div className="flex justify-between">
                <span>Mean reward:</span>
                <span className="font-mono font-medium text-text-primary">
                  {bandit?.summary.reward_avg != null
                    ? bandit.summary.reward_avg.toFixed(3)
                    : '—'}
                </span>
              </div>
              <div className="flex justify-between">
                <span>Promotion gate:</span>
                <span className="text-right text-[11px] text-text-muted">
                  Admin key + IPS ≥ live policy
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Right Graph Canvas (7 Cols) */}
        <div className="lg:col-span-7 space-y-4">
          <div className="panel p-5 space-y-4 rounded-xl">
            <div className="flex items-center justify-between border-b border-border-subtle pb-3">
              <div className="flex items-center gap-2">
                <Network className="w-4 h-4 text-apple-blue" />
                <h3 className="text-[13px] font-semibold text-text-primary">
                  Linked Entity Syndicate Topology
                </h3>
              </div>
              <span className="text-[11px] font-sans text-text-muted">
                Illustrative sample topology
              </span>
            </div>

            <FraudRingGraph
              height="440px"
              onNodeClick={handleNodeClick}
            />

            {selectedNode && (
              <div className="p-3 bg-surface-2 rounded-xl border border-border-subtle font-sans text-xs flex items-center justify-between">
                <span>
                  Selected Entity: <b className="font-mono text-apple-blue">{selectedNode.id}</b> ({selectedNode.type})
                </span>
                <button
                  onClick={() => setSelectedNode(null)}
                  className="btn-interactive text-xs text-text-muted hover:text-text-primary px-3 py-1 bg-surface-1 rounded-full border border-border-subtle"
                >
                  Clear Selection [ESC]
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      <InsightCallout title="Policy Thresholds &amp; Bandit Interaction">
        Transactions falling between the lower cutoff ({lowerThreshold.toFixed(2)}) and upper cutoff ({upperThreshold.toFixed(2)}) are routed to the manual review queue for human-in-the-loop analyst triage.
      </InsightCallout>
    </div>
  );
};
