import React, { useState } from 'react';
import { FraudRingGraph } from '../../components/charts/FraudRingGraph';
import { InsightCallout } from '../../components/ui/InsightCallout';
import { Sliders, GitMerge, Network } from 'lucide-react';

export const PolicyGraph: React.FC = () => {
  const [lowerThreshold, setLowerThreshold] = useState<number>(0.2);
  const [upperThreshold, setUpperThreshold] = useState<number>(0.8);
  const [selectedNode, setSelectedNode] = useState<{ id: string; type: string } | null>(null);

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between panel p-5 rounded-2xl">
        <div>
          <h2 className="text-sm font-sans font-bold text-text-primary tracking-tight uppercase">
            Decision Policy Engine &amp; Fraud Network Graph
          </h2>
          <p className="text-xs font-sans text-text-muted mt-0.5">
            Configure cutoff thresholds, monitor LinUCB contextual bandit exploration, and inspect syndicate clusters
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Left Policy Config (5 Cols) */}
        <div className="lg:col-span-5 space-y-4">
          <div className="panel p-5 space-y-4 rounded-2xl">
            <div className="flex items-center gap-2 border-b border-border-subtle pb-3">
              <Sliders className="w-4 h-4 text-apple-blue" />
              <h3 className="text-xs font-sans font-semibold uppercase tracking-wider text-text-primary">
                Decision Cutoff Thresholds (Policy v2.4)
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
                  onChange={(e) => setLowerThreshold(Number(e.target.value))}
                  className="w-full cursor-pointer accent-status-approve"
                />
                <span className="text-[11px] text-text-muted mt-1 block">
                  Scores &le; {lowerThreshold.toFixed(2)} are immediately approved.
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
                  min="0.6"
                  max="0.95"
                  step="0.01"
                  value={upperThreshold}
                  onChange={(e) => setUpperThreshold(Number(e.target.value))}
                  className="w-full cursor-pointer accent-status-block"
                />
                <span className="text-[11px] text-text-muted mt-1 block">
                  Scores &ge; {upperThreshold.toFixed(2)} are blocked instantly.
                </span>
              </div>

              {/* Threshold Visualizer Band */}
              <div className="p-4 bg-surface-2/90 rounded-2xl border border-border-subtle space-y-2 shadow-sm">
                <div className="text-xs font-medium text-text-secondary">Decision Spectrum:</div>
                <div className="h-4 w-full rounded-full overflow-hidden flex text-[10px] font-bold text-white text-center leading-4 shadow-inner p-0.5 bg-surface-1 border border-border-subtle">
                  <div
                    style={{ width: `${lowerThreshold * 100}%` }}
                    className="bg-gradient-to-r from-status-approve to-emerald-400 rounded-l-full"
                  >
                    APPROVE
                  </div>
                  <div
                    style={{ width: `${(upperThreshold - lowerThreshold) * 100}%` }}
                    className="bg-gradient-to-r from-status-review to-amber-400"
                  >
                    REVIEW
                  </div>
                  <div
                    style={{ width: `${(1 - upperThreshold) * 100}%` }}
                    className="bg-gradient-to-r from-status-block to-rose-500 rounded-r-full"
                  >
                    DECLINE
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Adaptive Contextual Bandit Layer */}
          <div className="panel p-5 space-y-3 font-sans text-xs rounded-2xl">
            <div className="flex items-center gap-2 border-b border-border-subtle pb-3">
              <GitMerge className="w-4 h-4 text-apple-indigo" />
              <h3 className="text-xs font-semibold uppercase tracking-wider text-text-primary">
                Adaptive Contextual Bandit Telemetry
              </h3>
            </div>

            <div className="space-y-2.5 text-text-secondary">
              <div className="flex justify-between">
                <span>Active Model:</span>
                <span className="text-text-primary font-bold font-mono">bandit_v2.json</span>
              </div>
              <div className="flex justify-between">
                <span>Random Exploration (ε):</span>
                <span className="text-text-primary font-mono font-medium">5.0% IPS Randomized</span>
              </div>
              <div className="flex justify-between">
                <span>Off-Policy Evaluator:</span>
                <span className="text-status-approve font-bold font-mono">IPS Reward: +0.892</span>
              </div>
              <div className="flex justify-between">
                <span>Promotion Gate:</span>
                <span className="text-status-approve font-semibold px-2 py-0.5 rounded-full bg-status-approve/12 border border-status-approve/30 text-[10px]">
                  Passed (Anti-Regression)
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Right Graph Canvas (7 Cols) */}
        <div className="lg:col-span-7 space-y-4">
          <div className="panel p-5 space-y-4 rounded-2xl">
            <div className="flex items-center justify-between border-b border-border-subtle pb-3">
              <div className="flex items-center gap-2">
                <Network className="w-4 h-4 text-apple-blue" />
                <h3 className="text-xs font-sans font-semibold uppercase tracking-wider text-text-primary">
                  Linked Entity Syndicate Topology
                </h3>
              </div>
              <span className="text-[11px] font-sans text-text-muted">Graph Partitioning Engine</span>
            </div>

            <FraudRingGraph
              height="360px"
              onNodeClick={(id, type) => setSelectedNode({ id, type })}
            />

            {selectedNode && (
              <div className="p-3 bg-surface-2/90 rounded-2xl border border-border-subtle font-sans text-xs flex items-center justify-between shadow-sm">
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
