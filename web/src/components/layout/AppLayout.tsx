import React from 'react';
import { NavLink, Outlet, useLocation } from 'react-router-dom';
import { useSSE } from '../../lib/sse';
import { useThemeStore } from '../../stores/useThemeStore';
import { useSelectedTxStore } from '../../stores/useSelectedTxStore';
import { Drawer } from '../ui/Drawer';
import { StatusBadge } from '../ui/StatusBadge';
import { ScoreBar } from '../ui/ScoreBar';
import {
  Shield,
  Sun,
  Moon,
  Activity,
  BarChart3,
  Sliders,
  Inbox,
  FileSpreadsheet,
  Network,
  History,
  Cpu,
} from 'lucide-react';

export const AppLayout: React.FC = () => {
  const { isConnected, latencyMs } = useSSE();
  const { theme, toggleTheme } = useThemeStore();
  const { selectedTx, isDrawerOpen, closeDrawer } = useSelectedTxStore();
  const location = useLocation();

  const navItems = [
    { path: '/', label: 'Live Radar', icon: Activity, badge: 'LIVE' },
    { path: '/impact', label: 'Exec Impact', icon: BarChart3 },
    { path: '/simulator', label: 'Simulator & XAI', icon: Sliders },
    { path: '/review', label: 'Review Queue', icon: Inbox },
    { path: '/batch', label: 'Batch Scanner', icon: FileSpreadsheet },
    { path: '/policy', label: 'Policy & Graph', icon: Network },
    { path: '/audit', label: 'Forensic Audit', icon: History },
    { path: '/model', label: 'Model MLOps', icon: Cpu },
  ];

  return (
    <div className="min-h-screen flex flex-col bg-bg-main text-text-primary">
      {/* Top Global Command Bar */}
      <header className="sticky top-0 z-40 bg-surface-1 border-b border-border-subtle px-4 lg:px-6 py-2 flex items-center justify-between">
        {/* Brand */}
        <div className="flex items-center gap-3">
          <div className="w-7 h-7 rounded-[2px] bg-surface-2 border border-border-subtle flex items-center justify-center text-text-primary">
            <Shield className="w-3.5 h-3.5 text-text-secondary" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-xs tracking-wider font-mono text-text-primary">
                LEDGER
              </span>
              <span className="text-[10px] font-mono font-medium px-1.5 py-0.2 rounded-[2px] bg-surface-2 border border-border-subtle text-text-secondary">
                v4.2 PROD
              </span>
            </div>
            <span className="text-[10px] font-mono text-text-muted hidden sm:block">
              Internal Decision Console · Fraud &amp; Compliance Operations
            </span>
          </div>
        </div>

        {/* Status Indicators & Controls */}
        <div className="flex items-center gap-2.5 font-mono text-xs">
          {/* Live Engine Stream Indicator */}
          <div className="flex items-center gap-2 px-2.5 py-1 bg-surface-2 rounded-[2px] border border-border-subtle text-xs">
            <span
              className={`w-2 h-2 rounded-full ${
                isConnected ? 'bg-status-approve' : 'bg-status-review'
              }`}
            />
            <span className="text-text-secondary text-[11px]">
              {isConnected ? 'STREAM CONNECTED' : 'CONNECTING...'}
            </span>
            <span className="text-text-muted text-[10px] pl-1 border-l border-border-subtle">
              {latencyMs}ms
            </span>
          </div>

          {/* Theme Toggle */}
          <button
            onClick={toggleTheme}
            className="p-1 rounded-[2px] bg-surface-2 hover:bg-surface-hover text-text-secondary hover:text-text-primary border border-border-subtle"
            title="Toggle theme"
            aria-label="Toggle theme"
          >
            {theme === 'dark' ? (
              <Sun className="w-3.5 h-3.5" />
            ) : (
              <Moon className="w-3.5 h-3.5" />
            )}
          </button>
        </div>
      </header>

      {/* Navigation Sub-Bar */}
      <nav className="sticky top-[45px] z-30 bg-surface-1 border-b border-border-subtle px-4 lg:px-6 py-1 overflow-x-auto">
        <div className="flex items-center gap-1 min-w-max">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path;

            return (
              <NavLink
                key={item.path}
                to={item.path}
                className={`flex items-center gap-1.5 px-2.5 py-1 rounded-[2px] text-xs font-mono transition-colors ${
                  isActive
                    ? 'bg-surface-2 text-text-primary font-bold border border-border-subtle'
                    : 'text-text-secondary hover:text-text-primary hover:bg-surface-hover'
                }`}
              >
                <Icon className="w-3 h-3 text-text-muted" />
                <span>{item.label}</span>
                {item.badge && (
                  <span className="text-[9px] font-bold px-1 py-0.2 rounded-[2px] bg-surface-2 text-status-approve border border-status-approve/30">
                    {item.badge}
                  </span>
                )}
              </NavLink>
            );
          })}
        </div>
      </nav>

      {/* Main View Area */}
      <main className="flex-1 p-4 lg:p-6 max-w-7xl w-full mx-auto animate-fade-in">
        <Outlet />
      </main>

      {/* Deep Forensics Slide-Over Drawer */}
      <Drawer
        isOpen={isDrawerOpen}
        onClose={closeDrawer}
        title={`Transaction Forensics: #${selectedTx?.transaction_id?.slice(-8) || ''}`}
        subtitle={`ID: ${selectedTx?.transaction_id || ''}`}
      >
        {selectedTx && (
          <div className="space-y-4 text-xs font-mono">
            {/* Decision Bar */}
            <div className="p-3.5 bg-surface-2 rounded-[4px] border border-border-subtle flex items-center justify-between">
              <div>
                <span className="text-[10px] text-text-muted block mb-1 uppercase tracking-wider">
                  Outcome Decision:
                </span>
                <StatusBadge status={selectedTx.decision} size="lg" />
              </div>
              <div className="text-right">
                <span className="text-[10px] text-text-muted block mb-0.5 uppercase tracking-wider">
                  Probability Score:
                </span>
                <span className="text-lg font-bold font-mono text-text-primary tabular-nums">
                  {(selectedTx.score * 100).toFixed(1)}%
                </span>
              </div>
            </div>

            {/* ScoreBar Instrument Track */}
            <div className="panel p-3">
              <span className="text-[10px] text-text-muted uppercase tracking-wider block mb-1">
                Risk Distribution Track
              </span>
              <ScoreBar probability={selectedTx.score} showPercentage={true} />
            </div>

            {/* Meta Table */}
            <div className="space-y-1.5">
              <h4 className="text-text-secondary font-semibold uppercase tracking-wider text-[11px]">
                Inference &amp; Policy Metadata
              </h4>
              <div className="divide-y divide-border-subtle/50 panel p-3 space-y-1.5 text-text-secondary">
                <div className="flex justify-between pt-1">
                  <span>Timestamp (UTC):</span>
                  <span className="text-text-primary font-mono">{selectedTx.timestamp}</span>
                </div>
                <div className="flex justify-between pt-1">
                  <span>Model Version:</span>
                  <span className="text-text-primary font-mono">{selectedTx.model_version}</span>
                </div>
                <div className="flex justify-between pt-1">
                  <span>Policy Version:</span>
                  <span className="text-text-primary font-mono">{selectedTx.policy_version || '2.4'}</span>
                </div>
                <div className="flex justify-between pt-1">
                  <span>Policy Action:</span>
                  <span className="text-text-primary font-mono">{selectedTx.action || 'Default Policy'}</span>
                </div>
                <div className="flex justify-between pt-1">
                  <span>Reviewer Outcome:</span>
                  <span className="font-bold text-text-primary font-mono">{selectedTx.reviewer_outcome || 'Pending'}</span>
                </div>
              </div>
            </div>

            {/* Input Features Payload */}
            {selectedTx.input_features && (
              <div className="space-y-1.5">
                <h4 className="text-text-secondary font-semibold uppercase tracking-wider text-[11px]">
                  Raw Input Features Payload
                </h4>
                <pre className="p-3 panel text-[11px] text-text-primary overflow-x-auto max-h-48">
                  {JSON.stringify(selectedTx.input_features, null, 2)}
                </pre>
              </div>
            )}
          </div>
        )}
      </Drawer>
    </div>
  );
};
