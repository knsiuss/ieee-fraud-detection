import React, { useState } from 'react';
import { FraudRingGraph } from '../../components/charts/FraudRingGraph';
import { InsightCallout } from '../../components/ui/InsightCallout';
import { Sliders, GitMerge, Network } from 'lucide-react';

export const PolicyGraph: React.FC = () => {
  const [lowerThreshold, setLowerThreshold] = useState<number>(0.2);
  const [upperThreshold, setUpperThreshold] = useState<number>(0.8);
  const [selectedNode, setSelectedNode] = useState<{ id: string; type: string } | null>(null);

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between panel p-3.5">
        <div>
          <h2 className="text-sm font-mono font-bold text-text-primary tracking-tight">
            DECISION POLICY ENGINE &amp; FRAUD NETWORK GRAPH
          </h2>
          <p className="text-xs font-mono text-text-muted">
            Configure cutoff thresholds, monitor LinUCB contextual bandit exploration, and inspect syndicate clusters
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Left Policy Config (5 Cols) */}
        <div className="lg:col-span-5 space-y-4">
          <div className="panel p-4 space-y-3">
            <div className="flex items-center gap-1.5 border-b border-border-subtle pb-2">
              <Sliders className="w-3.5 h-3.5 text-text-muted" />
              <h3 className="text-xs font-mono font-semibold uppercase tracking-wider text-text-primary">
                Decision Cutoff Thresholds (Policy v2.4)
              </h3>
            </div>

            <div className="space-y-3 font-mono text-xs">
              {/* Lower Threshold */}
              <div>
                <div className="flex justify-between mb-1">
                  <span className="text-text-secondary">Auto-Approve Cutoff:</span>
                  <span className="text-status-approve font-bold tabular-nums">{lowerThreshold.toFixed(2)}</span>
                </div>
                <input
                  type="range"
                  min="0.05"
                  max="0.4"
                  step="0.01"
                  value={lowerThreshold}
                  onChange={(e) => setLowerThreshold(Number(e.target.value))}
                  className="w-full cursor-pointer"
                />
                <span className="text-[10px] text-text-muted">
                  Scores &le; {lowerThreshold.toFixed(2)} are immediately approved.
                </span>
              </div>

              {/* Upper Threshold */}
              <div>
                <div className="flex justify-between mb-1">
                  <span className="text-text-secondary">Auto-Decline Cutoff:</span>
                  <span className="text-status-block font-bold tabular-nums">{upperThreshold.toFixed(2)}</span>
                </div>
                <input
                  type="range"
                  min="0.6"
                  max="0.95"
                  step="0.01"
                  value={upperThreshold}
                  onChange={(e) => setUpperThreshold(Number(e.target.value))}
                  className="w-full cursor-pointer"
                />
                <span className="text-[10px] text-text-muted">
                  Scores &ge; {upperThreshold.toFixed(2)} are blocked instantly.
                </span>
              </div>

              {/* Threshold Visualizer Band */}
              <div className="p-2.5 bg-surface-2 rounded-[6px] border border-border-subtle space-y-1.5">
                <div className="text-[10px] text-text-secondary">Decision Spectrum:</div>
                <div className="h-3.5 w-full rounded-[6px] overflow-hidden flex text-[9px] font-bold text-white text-center leading-[14px]">
                  <div
                    style={{ width: `${lowerThreshold * 100}%` }}
                    className="bg-status-approve"
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
                    className="bg-status-block"
                  >
                    DECLINE
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Adaptive Contextual Bandit Layer */}
          <div className="panel p-4 space-y-2.5 font-mono text-xs">
            <div className="flex items-center gap-1.5 border-b border-border-subtle pb-2">
              <GitMerge className="w-3.5 h-3.5 text-text-muted" />
              <h3 className="text-xs font-semibold uppercase tracking-wider text-text-primary">
                Adaptive Contextual Bandit Telemetry
              </h3>
            </div>

            <div className="space-y-1.5 text-text-secondary">
              <div className="flex justify-between">
                <span>Active Model:</span>
                <span className="text-text-primary font-bold">bandit_v2.json</span>
              </div>
              <div className="flex justify-between">
                <span>Random Exploration (ε):</span>
                <span className="text-text-primary">5.0% IPS Randomized</span>
              </div>
              <div className="flex justify-between">
                <span>Off-Policy Evaluator:</span>
                <span className="text-status-approve font-bold">IPS Reward: +0.892</span>
              </div>
              <div className="flex justify-between">
                <span>Promotion Gate:</span>
                <span className="text-status-approve font-bold">Passed (Anti-Regression)</span>
              </div>
            </div>
          </div>
        </div>

        {/* Right Graph Canvas (7 Cols) */}
        <div className="lg:col-span-7 space-y-4">
          <div className="panel p-4 space-y-3">
            <div className="flex items-center justify-between border-b border-border-subtle pb-2">
              <div className="flex items-center gap-1.5">
                <Network className="w-3.5 h-3.5 text-text-muted" />
                <h3 className="text-xs font-mono font-semibold uppercase tracking-wider text-text-primary">
                  Linked Entity Syndicate Topology
                </h3>
              </div>
              <span className="text-[10px] font-mono text-text-muted">Graph Partitioning Engine</span>
            </div>

            <FraudRingGraph
              height="340px"
              onNodeClick={(id, type) => setSelectedNode({ id, type })}
            />

            {selectedNode && (
              <div className="p-2.5 bg-surface-2 rounded-[6px] border border-border-subtle font-mono text-xs flex items-center justify-between">
                <span>
                  Selected Entity: <b>{selectedNode.id}</b> ({selectedNode.type})
                </span>
                <button
                  onClick={() => setSelectedNode(null)}
                  className="btn-interactive text-[11px] text-text-muted hover:text-text-primary"
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
