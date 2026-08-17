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
    <div className="min-h-screen flex flex-col bg-bg-main text-text-primary selection:bg-status-approve/20 selection:text-text-primary">
      {/* Top Global Apple Frosted Command Bar */}
      <header className="sticky top-0 z-40 bg-surface-1/80 backdrop-blur-2xl border-b border-border-subtle px-4 lg:px-8 py-3 flex items-center justify-between transition-all">
        {/* Brand & System Status */}
        <div className="flex items-center gap-3.5">
          <div className="w-8 h-8 rounded-2xl bg-gradient-to-tr from-surface-2 to-surface-hover flex items-center justify-center text-text-primary border border-border-subtle shadow-sm transition-transform hover:scale-105">
            <Shield className="w-4 h-4 text-apple-blue" />
          </div>
          <div>
            <div className="flex items-center gap-2.5">
              <span className="font-semibold text-sm tracking-tight text-text-primary font-sans">
                Sentinel
              </span>
              <span className="text-[10px] font-mono font-medium px-2.5 py-0.5 rounded-full bg-surface-2/80 text-text-secondary border border-border-subtle">
                v4.5 HIG
              </span>
            </div>
            <span className="text-[11px] text-text-muted hidden sm:block font-normal">
              Autonomous Risk Intelligence &amp; Decisioning Console
            </span>
          </div>
        </div>

        {/* Status Indicators & Controls */}
        <div className="flex items-center gap-3">
          {/* Live Engine Stream Indicator Pill */}
          <div className="flex items-center gap-2 px-3 py-1.5 bg-surface-2/80 rounded-full text-xs border border-border-subtle shadow-sm backdrop-blur-md">
            <span className="relative flex h-2 w-2">
              {isConnected && (
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-status-approve opacity-75" />
              )}
              <span
                className={`relative inline-flex rounded-full h-2 w-2 ${isConnected ? 'bg-status-approve' : 'bg-status-review'
                  }`}
              />
            </span>
            <span className="text-text-secondary text-[11px] font-medium tracking-tight font-sans">
              {isConnected ? 'Stream Active' : 'Connecting...'}
            </span>
            <span className="text-text-muted text-[10px] font-mono pl-1.5 border-l border-border-subtle">
              {latencyMs}ms
            </span>
          </div>

          {/* Theme Toggle Pill */}
          <button
            onClick={toggleTheme}
            className="p-2 rounded-full bg-surface-2/80 hover:bg-surface-hover text-text-secondary hover:text-text-primary transition-all duration-200 border border-border-subtle shadow-sm hover:scale-105 active:scale-95 cursor-pointer"
            title="Toggle theme"
            aria-label="Toggle theme"
          >
            {theme === 'dark' ? (
              <Sun className="w-3.5 h-3.5 text-amber-300" />
            ) : (
              <Moon className="w-3.5 h-3.5 text-slate-700" />
            )}
          </button>
        </div>
      </header>

      {/* Apple Floating Navigation Dock Bar */}
      <nav className="sticky top-[57px] z-30 bg-surface-1/70 backdrop-blur-xl border-b border-border-subtle/80 px-4 lg:px-8 py-2 overflow-x-auto">
        <div className="flex items-center gap-1.5 min-w-max">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path;

            return (
              <NavLink
                key={item.path}
                to={item.path}
                className={`flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-medium transition-all duration-200 ${isActive
                    ? 'bg-surface-hover text-text-primary font-semibold shadow-sm border border-border-highlight scale-[1.02]'
                    : 'text-text-secondary hover:text-text-primary hover:bg-surface-2/60 hover:scale-[1.01]'
                  }`}
              >
                <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-apple-blue' : 'text-text-muted'}`} />
                <span>{item.label}</span>
                {item.badge && (
                  <span className="text-[9px] font-bold px-1.5 py-0.5 rounded-full bg-status-approve/15 text-status-approve border border-status-approve/30 animate-pulse">
                    {item.badge}
                  </span>
                )}
              </NavLink>
            );
          })}
        </div>
      </nav>

      {/* Main View Area */}
      <main className="flex-1 p-4 lg:p-8 max-w-7xl w-full mx-auto animate-fade-in">
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
          <div className="space-y-4 text-xs font-sans">
            {/* Decision Bar */}
            <div className="p-4 bg-surface-2 rounded-2xl border border-border-subtle flex items-center justify-between shadow-sm">
              <div>
                <span className="text-[10px] text-text-muted block mb-1 uppercase tracking-wider font-semibold">
                  Outcome Decision
                </span>
                <StatusBadge status={selectedTx.decision} size="lg" />
              </div>
              <div className="text-right">
                <span className="text-[10px] text-text-muted block mb-0.5 uppercase tracking-wider font-semibold">
                  Probability Score
                </span>
                <span className="text-xl font-bold font-mono text-text-primary tabular-nums tracking-tight">
                  {(selectedTx.score * 100).toFixed(1)}%
                </span>
              </div>
            </div>

            {/* ScoreBar Instrument Track */}
            <div className="panel p-4 rounded-2xl">
              <span className="text-[10px] text-text-muted uppercase tracking-wider block mb-2 font-semibold">
                Risk Distribution Track
              </span>
              <ScoreBar probability={selectedTx.score} showPercentage={true} />
            </div>

            {/* Meta Table */}
            <div className="space-y-2">
              <h4 className="text-text-secondary font-semibold uppercase tracking-wider text-[11px] px-1">
                Inference &amp; Policy Metadata
              </h4>
              <div className="divide-y divide-border-subtle/50 panel p-4 space-y-2 text-text-secondary rounded-2xl">
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
              <div className="space-y-2">
                <h4 className="text-text-secondary font-semibold uppercase tracking-wider text-[11px] px-1">
                  Raw Input Features Payload
                </h4>
                <pre className="p-4 panel rounded-2xl text-[11px] text-text-primary overflow-x-auto max-h-48 font-mono">
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
