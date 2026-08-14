import React, { useState } from 'react';
import { FraudRingGraph } from '../../components/charts/FraudRingGraph';
import { InsightCallout } from '../../components/ui/InsightCallout';
import { Sliders, GitMerge, ShieldCheck, Network, Layers, AlertOctagon } from 'lucide-react';

export const PolicyGraph: React.FC = () => {
  const [lowerThreshold, setLowerThreshold] = useState<number>(0.2);
  const [upperThreshold, setUpperThreshold] = useState<number>(0.8);
  const [selectedNode, setSelectedNode] = useState<{ id: string; type: string } | null>(null);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between bg-surface-1 border border-border-subtle p-4 rounded-lg">
        <div>
          <h2 className="text-base font-bold text-text-primary tracking-tight">
            DECISION POLICY ENGINE &amp; FRAUD NETWORK GRAPH
          </h2>
          <p className="text-xs font-mono text-text-muted">
            Configure cutoff thresholds, adaptive contextual bandit exploration, and explore linked syndicate clusters
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Policy Config (5 Cols) */}
        <div className="lg:col-span-5 space-y-4">
          <div className="bg-surface-1 border border-border-subtle rounded-lg p-5 space-y-4">
            <div className="flex items-center gap-2 border-b border-border-subtle pb-3">
              <Sliders className="w-4 h-4 text-accent-teal" />
              <h3 className="text-xs font-semibold uppercase tracking-wider text-text-primary">
                Decision Thresholds Policy (v2.4)
              </h3>
            </div>

            <div className="space-y-4 font-mono text-xs">
              {/* Lower Threshold */}
              <div>
                <div className="flex justify-between mb-1.5">
                  <span className="text-text-secondary">Auto-Approve Cutoff (Lower):</span>
                  <span className="text-status-approve font-bold">{lowerThreshold.toFixed(2)}</span>
                </div>
                <input
                  type="range"
                  min="0.05"
                  max="0.4"
                  step="0.01"
                  value={lowerThreshold}
                  onChange={(e) => setLowerThreshold(Number(e.target.value))}
                  className="w-full accent-accent-teal cursor-pointer"
                />
                <span className="text-[11px] text-text-muted">
                  Transactions with score &le; {lowerThreshold.toFixed(2)} are immediately cleared.
                </span>
              </div>

              {/* Upper Threshold */}
              <div>
                <div className="flex justify-between mb-1.5">
                  <span className="text-text-secondary">Auto-Decline Cutoff (Upper):</span>
                  <span className="text-status-block font-bold">{upperThreshold.toFixed(2)}</span>
                </div>
                <input
                  type="range"
                  min="0.6"
                  max="0.95"
                  step="0.01"
                  value={upperThreshold}
                  onChange={(e) => setUpperThreshold(Number(e.target.value))}
                  className="w-full accent-status-block cursor-pointer"
                />
                <span className="text-[11px] text-text-muted">
                  Transactions with score &ge; {upperThreshold.toFixed(2)} are blocked instantly.
                </span>
              </div>

              {/* Threshold Visualizer Band */}
              <div className="p-3 bg-surface-2 rounded-lg border border-border-subtle space-y-2">
                <div className="text-[11px] text-text-secondary">Decision Spectrum:</div>
                <div className="h-4 w-full rounded overflow-hidden flex text-[10px] font-bold text-black text-center leading-4">
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
                    BLOCK
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Adaptive Contextual Bandit Layer */}
          <div className="bg-surface-1 border border-border-subtle rounded-lg p-5 space-y-3 font-mono text-xs">
            <div className="flex items-center gap-2 border-b border-border-subtle pb-3">
              <GitMerge className="w-4 h-4 text-accent-cyan" />
              <h3 className="text-xs font-semibold uppercase tracking-wider text-text-primary">
                Adaptive Contextual Bandit (Feature 1)
              </h3>
            </div>

            <div className="space-y-2 text-text-secondary">
              <div className="flex justify-between">
                <span>Bandit Policy:</span>
                <span className="text-accent-teal font-bold">bandit_v2.json (Active)</span>
              </div>
              <div className="flex justify-between">
                <span>Exploration Propensity (ε):</span>
                <span className="text-text-primary">5.0% IPS Randomized</span>
              </div>
              <div className="flex justify-between">
                <span>Off-Policy Evaluator:</span>
                <span className="text-status-approve">IPS Reward: +0.892</span>
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
          <div className="bg-surface-1 border border-border-subtle rounded-lg p-5 space-y-3">
            <div className="flex items-center justify-between border-b border-border-subtle pb-3">
              <div className="flex items-center gap-2">
                <Network className="w-4 h-4 text-accent-cyan" />
                <h3 className="text-xs font-semibold uppercase tracking-wider text-text-primary">
                  Syndicate &amp; Entity Correlation Graph
                </h3>
              </div>
              <span className="text-[11px] font-mono text-text-muted">
                Interactive Cytoscape Network
              </span>
            </div>

            <FraudRingGraph
              height="380px"
              onNodeClick={(id, type) => setSelectedNode({ id, type })}
            />

            {selectedNode && (
              <div className="p-3 bg-surface-2 rounded-lg border border-accent-teal/30 text-xs font-mono flex items-center justify-between">
                <span className="text-text-secondary">
                  Selected Entity: <b className="text-text-primary font-bold">{selectedNode.id}</b> ({selectedNode.type})
                </span>
                <span className="text-status-block font-semibold">Syndicate Risk: High</span>
              </div>
            )}
          </div>
        </div>
      </div>

      <InsightCallout title="Graph Intelligence & Entity Linking" variant="warning">
        Graph neural network clustering isolates card-testing botnets by tracking shared IP subnets, browser canvas fingerprints, and disposable email domains across multiple transactions.
      </InsightCallout>
    </div>
  );
};
