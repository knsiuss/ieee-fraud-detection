import React from 'react';
import { NavLink, Outlet, useLocation } from 'react-router-dom';
import { useSSE } from '../../lib/sse';
import { useThemeStore } from '../../stores/useThemeStore';
import { useSelectedTxStore } from '../../stores/useSelectedTxStore';
import { Drawer } from '../ui/Drawer';
import { StatusBadge } from '../ui/StatusBadge';
import { GaugeChart } from '../charts/GaugeChart';
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
    <div className="min-h-screen flex flex-col bg-background text-text-primary">
      {/* Top Global Command Bar */}
      <header className="sticky top-0 z-40 bg-surface-1/95 backdrop-blur border-b border-border-subtle px-4 lg:px-8 py-2.5 flex items-center justify-between">
        {/* Brand */}
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-accent-teal/15 border border-accent-teal/30 flex items-center justify-center text-accent-teal">
            <Shield className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-sm tracking-wider font-mono">SENTINEL</span>
              <span className="text-[10px] font-mono font-semibold px-1.5 py-0.2 rounded bg-surface-2 border border-border-subtle text-accent-cyan">
                v4.0 PROD
              </span>
            </div>
            <span className="text-[11px] text-text-muted hidden sm:block">
              IEEE-CIS Real-Time Fraud Defense Engine
            </span>
          </div>
        </div>

        {/* Status Indicators & Controls */}
        <div className="flex items-center gap-3 font-mono text-xs">
          {/* Live Engine Stream Pulse */}
          <div className="flex items-center gap-2 px-2.5 py-1 bg-surface-2 rounded-md border border-border-subtle">
            <span className="relative flex h-2 w-2">
              <span
                className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${
                  isConnected ? 'bg-status-approve' : 'bg-status-review'
                }`}
              />
              <span
                className={`relative inline-flex rounded-full h-2 w-2 ${
                  isConnected ? 'bg-status-approve' : 'bg-status-review'
                }`}
              />
            </span>
            <span className="text-text-secondary text-[11px]">
              {isConnected ? 'STREAM ACTIVE' : 'CONNECTING...'}
            </span>
            <span className="text-text-muted text-[10px] pl-1 border-l border-border-subtle">
              {latencyMs}ms
            </span>
          </div>

          {/* Theme Toggle */}
          <button
            onClick={toggleTheme}
            className="p-1.5 rounded-md bg-surface-2 hover:bg-surface-hover text-text-secondary hover:text-text-primary border border-border-subtle transition-colors"
            title="Toggle theme"
          >
            {theme === 'dark' ? <Sun className="w-4 h-4 text-accent-teal" /> : <Moon className="w-4 h-4 text-accent-sky" />}
          </button>
        </div>
      </header>

      {/* Navigation Sub-Bar */}
      <nav className="bg-surface-1 border-b border-border-subtle px-4 lg:px-8 py-2 overflow-x-auto">
        <div className="flex items-center gap-1.5 min-w-max">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path;

            return (
              <NavLink
                key={item.path}
                to={item.path}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-mono transition-all duration-150 relative ${
                  isActive
                    ? 'bg-surface-2 text-text-primary font-bold shadow-xs'
                    : 'text-text-secondary hover:text-text-primary hover:bg-surface-hover/60'
                }`}
              >
                <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-accent-teal' : 'opacity-70'}`} />
                <span>{item.label}</span>
                {item.badge && (
                  <span className="text-[9px] font-bold px-1 rounded bg-status-approve/20 text-status-approve">
                    {item.badge}
                  </span>
                )}
                {isActive && (
                  <span className="absolute bottom-0 left-2 right-2 h-[2px] bg-accent-teal rounded-full" />
                )}
              </NavLink>
            );
          })}
        </div>
      </nav>

      {/* Main View Area */}
      <main className="flex-1 p-4 lg:p-8 max-w-7xl w-full mx-auto">
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
          <div className="space-y-6 text-xs font-mono">
            {/* Decision Bar */}
            <div className="p-4 bg-surface-2 rounded-lg border border-border-subtle flex items-center justify-between">
              <div>
                <span className="text-[11px] text-text-muted block">Outcome Decision:</span>
                <StatusBadge status={selectedTx.decision} size="lg" />
              </div>
              <div className="text-right">
                <span className="text-[11px] text-text-muted block">Fraud Probability:</span>
                <span
                  className={`text-xl font-bold ${
                    selectedTx.score > 0.8
                      ? 'text-status-block'
                      : selectedTx.score > 0.2
                      ? 'text-status-review'
                      : 'text-status-approve'
                  }`}
                >
                  {(selectedTx.score * 100).toFixed(1)}%
                </span>
              </div>
            </div>

            {/* Gauge */}
            <div className="p-2 bg-surface-2/50 rounded-lg border border-border-subtle">
              <GaugeChart score={selectedTx.score} height="200px" />
            </div>

            {/* Meta Table */}
            <div className="space-y-2">
              <h4 className="text-text-secondary font-semibold uppercase tracking-wider text-[11px]">
                Inference &amp; Policy Metadata
              </h4>
              <div className="divide-y divide-border-subtle/50 bg-surface-2 rounded-lg border border-border-subtle p-3 space-y-1.5 text-text-secondary">
                <div className="flex justify-between pt-1">
                  <span>Timestamp (UTC):</span>
                  <span className="text-text-primary">{selectedTx.timestamp}</span>
                </div>
                <div className="flex justify-between pt-1">
                  <span>Model Version:</span>
                  <span className="text-accent-cyan">{selectedTx.model_version}</span>
                </div>
                <div className="flex justify-between pt-1">
                  <span>Policy Version:</span>
                  <span className="text-text-primary">{selectedTx.policy_version || '2.4'}</span>
                </div>
                <div className="flex justify-between pt-1">
                  <span>Policy Action:</span>
                  <span className="text-text-primary">{selectedTx.action || 'Default Policy'}</span>
                </div>
                <div className="flex justify-between pt-1">
                  <span>Reviewer Outcome:</span>
                  <span className="font-bold text-text-primary">{selectedTx.reviewer_outcome || 'Pending'}</span>
                </div>
              </div>
            </div>

            {/* Input Features Payload */}
            {selectedTx.input_features && (
              <div className="space-y-2">
                <h4 className="text-text-secondary font-semibold uppercase tracking-wider text-[11px]">
                  Raw Input Features Payload
                </h4>
                <pre className="p-3 bg-surface-2 rounded-lg border border-border-subtle text-[11px] text-accent-sky overflow-x-auto max-h-48">
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
