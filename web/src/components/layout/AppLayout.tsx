import React from 'react';
import { NavLink, Outlet, useLocation } from 'react-router-dom';
import { useSSE } from '../../lib/sse';
import { useThemeStore } from '../../stores/useThemeStore';
import { useSelectedTxStore } from '../../stores/useSelectedTxStore';
import { Drawer } from '../ui/Drawer';
import { StatusBadge } from '../ui/StatusBadge';
import { ScoreBar } from '../ui/ScoreBar';
import {
  Activity,
  BarChart3,
  Sliders,
  Inbox,
  FileSpreadsheet,
  Network,
  History,
  Cpu,
  Sun,
  Moon,
  ChevronRight,
} from 'lucide-react';

interface NavItem {
  path: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  live?: boolean;
}

const NAV_GROUPS: Array<{ label: string; items: NavItem[] }> = [
  {
    label: 'Monitoring',
    items: [
      { path: '/', label: 'Live Radar', icon: Activity, live: true },
      { path: '/impact', label: 'Exec Impact', icon: BarChart3 },
    ],
  },
  {
    label: 'Operations',
    items: [
      { path: '/review', label: 'Review Queue', icon: Inbox },
      { path: '/audit', label: 'Forensic Audit', icon: History },
    ],
  },
  {
    label: 'Analysis',
    items: [
      { path: '/simulator', label: 'Simulator & XAI', icon: Sliders },
      { path: '/batch', label: 'Batch Scanner', icon: FileSpreadsheet },
      { path: '/policy', label: 'Policy & Graph', icon: Network },
    ],
  },
  {
    label: 'Platform',
    items: [{ path: '/model', label: 'Model Operations', icon: Cpu }],
  },
];

const PAGE_META: Record<string, { title: string; subtitle: string }> = {
  '/': { title: 'Live Radar', subtitle: 'Real-time decisioning and fraud operations' },
  '/impact': { title: 'Executive Impact', subtitle: 'Fraud losses prevented and portfolio economics' },
  '/simulator': { title: 'Decision Simulator', subtitle: 'Score a transaction and inspect model explanations' },
  '/review': { title: 'Review Queue', subtitle: 'Human-in-the-loop case dispositions' },
  '/batch': { title: 'Batch Scanner', subtitle: 'Score transaction files at throughput' },
  '/policy': { title: 'Policy & Decision Graph', subtitle: 'Decision policy, adaptive layer and network topology' },
  '/audit': { title: 'Forensic Audit', subtitle: 'Decision ledger, appeals and compliance trail' },
  '/model': { title: 'Model Operations', subtitle: 'Served model, drift monitoring and retraining' },
};

const StreamStatus: React.FC<{ isConnected: boolean; latencyMs: number }> = ({
  isConnected,
  latencyMs,
}) => (
  <span className="control h-8 gap-2">
    <span
      className={`h-1.5 w-1.5 rounded-full ${isConnected ? 'bg-status-approve' : 'bg-status-review'}`}
    />
    <span className="text-[11.5px]">{isConnected ? 'Live' : 'Connecting'}</span>
    <span className="border-l border-border-subtle pl-2 font-mono text-[11px] text-text-muted">
      {latencyMs}ms
    </span>
  </span>
);

export const AppLayout: React.FC = () => {
  const { isConnected, latencyMs } = useSSE();
  const { theme, toggleTheme } = useThemeStore();
  const { selectedTx, isDrawerOpen, closeDrawer } = useSelectedTxStore();
  const location = useLocation();

  const meta = PAGE_META[location.pathname] ?? PAGE_META['/'];

  const themeButton = (
    <button
      onClick={toggleTheme}
      className="control h-8 w-8 justify-center p-0"
      title="Toggle theme"
      aria-label="Toggle theme"
    >
      {theme === 'dark' ? <Sun className="h-3.5 w-3.5" /> : <Moon className="h-3.5 w-3.5" />}
    </button>
  );

  return (
    <div className="min-h-screen bg-bg-main text-text-primary">
      {/* ── Sidebar (desktop) ─────────────────────────────────────────── */}
      <aside className="fixed inset-y-0 left-0 z-40 hidden w-[232px] flex-col border-r border-border-subtle bg-surface-1 lg:flex">
        <div className="flex items-center gap-2.5 px-5 py-4">
          <div className="flex h-8 w-8 items-center justify-center overflow-hidden rounded-lg border border-border-subtle bg-surface-2">
            <img src="/logo.jpg" alt="Sentinel" className="h-full w-full object-cover" />
          </div>
          <div className="min-w-0">
            <div className="truncate text-[13.5px] font-semibold tracking-tight">Sentinel</div>
            <div className="truncate text-[11px] text-text-muted">Fraud Decisioning</div>
          </div>
        </div>

        <nav className="flex-1 space-y-5 overflow-y-auto px-3 py-3">
          {NAV_GROUPS.map((group) => (
            <div key={group.label}>
              <div className="eyebrow px-2 pb-1.5">{group.label}</div>
              <div className="space-y-0.5">
                {group.items.map((item) => {
                  const Icon = item.icon;
                  return (
                    <NavLink
                      key={item.path}
                      to={item.path}
                      className={({ isActive }) =>
                        `group flex h-8 items-center gap-2.5 rounded-md px-2 text-[12.5px] font-medium transition-colors ${
                          isActive
                            ? 'bg-surface-2 text-text-primary'
                            : 'text-text-secondary hover:bg-surface-2 hover:text-text-primary'
                        }`
                      }
                    >
                      {({ isActive }) => (
                        <>
                          <Icon
                            className={`h-4 w-4 shrink-0 ${
                              isActive ? 'text-apple-blue' : 'text-text-muted'
                            }`}
                          />
                          <span className="truncate">{item.label}</span>
                          {item.live && (
                            <span className="ml-auto flex items-center gap-1 text-[10px] text-text-muted">
                              <span className="h-1.5 w-1.5 rounded-full bg-status-approve" />
                              LIVE
                            </span>
                          )}
                        </>
                      )}
                    </NavLink>
                  );
                })}
              </div>
            </div>
          ))}
        </nav>

        <div className="border-t border-border-subtle px-5 py-3">
          <div className="flex items-center justify-between text-[11px] text-text-muted">
            <span>Environment</span>
            <span className="flex items-center gap-1.5 text-text-secondary">
              <span className="h-1.5 w-1.5 rounded-full bg-status-approve" />
              Local
            </span>
          </div>
          <div className="mt-1 flex items-center justify-between text-[11px] text-text-muted">
            <span>Policy</span>
            <span className="font-mono text-text-secondary">threshold v1</span>
          </div>
        </div>
      </aside>

      {/* ── Main column ──────────────────────────────────────────────── */}
      <div className="flex min-h-screen flex-col lg:pl-[232px]">
        <header className="sticky top-0 z-30 flex h-14 items-center justify-between gap-4 border-b border-border-subtle bg-bg-main px-4 lg:px-7">
          <div className="flex min-w-0 items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center overflow-hidden rounded-lg border border-border-subtle bg-surface-2 lg:hidden">
              <img src="/logo.jpg" alt="Sentinel" className="h-full w-full object-cover" />
            </div>
            <nav
              aria-label="Breadcrumb"
              className="hidden min-w-0 items-center gap-1.5 text-[12px] lg:flex"
            >
              <span className="text-text-muted">Sentinel</span>
              <ChevronRight className="h-3 w-3 shrink-0 text-text-muted" />
              <span className="truncate font-medium text-text-primary">{meta.title}</span>
            </nav>
          </div>

          <div className="flex shrink-0 items-center gap-2">
            <StreamStatus isConnected={isConnected} latencyMs={latencyMs} />
            {themeButton}
          </div>
        </header>

        {/* Mobile navigation */}
        <nav className="sticky top-14 z-20 flex gap-1 overflow-x-auto border-b border-border-subtle bg-surface-1 px-3 lg:hidden">
          {NAV_GROUPS.flatMap((g) => g.items).map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                `whitespace-nowrap border-b-2 px-2.5 py-2.5 text-[12px] font-medium transition-colors ${
                  isActive
                    ? 'border-apple-blue text-text-primary'
                    : 'border-transparent text-text-secondary hover:text-text-primary'
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>

        <main className="flex-1">
          <div className="mx-auto w-full max-w-[1600px] animate-fade-in px-4 py-5 lg:px-7 lg:py-6">
            <Outlet />
          </div>
        </main>
      </div>

      {/* ── Transaction drawer ───────────────────────────────────────── */}
      <Drawer
        isOpen={isDrawerOpen}
        onClose={closeDrawer}
        title={`Transaction #${selectedTx?.transaction_id?.slice(-8) || ''}`}
        subtitle={`ID: ${selectedTx?.transaction_id || ''}`}
      >
        {selectedTx && (
          <div className="space-y-4 text-xs">
            <div className="flex items-center justify-between rounded-xl border border-border-subtle bg-surface-2 p-4">
              <div>
                <span className="eyebrow mb-1 block">Decision</span>
                <StatusBadge status={selectedTx.decision} size="lg" />
              </div>
              <div className="text-right">
                <span className="eyebrow mb-1 block">Fraud probability</span>
                <span className="font-mono text-xl font-semibold tabular-nums tracking-tight text-text-primary">
                  {(selectedTx.score * 100).toFixed(1)}%
                </span>
              </div>
            </div>

            <div className="panel p-4">
              <span className="eyebrow mb-2 block">Risk distribution</span>
              <ScoreBar probability={selectedTx.score} showPercentage={true} />
            </div>

            <div className="space-y-2">
              <h4 className="eyebrow px-1">Inference &amp; policy metadata</h4>
              <div className="space-y-2 rounded-xl border border-border-subtle bg-surface-2 p-4 text-text-secondary">
                {[
                  ['Timestamp (UTC)', selectedTx.timestamp],
                  ['Model version', selectedTx.model_version],
                  ['Policy version', selectedTx.policy_version || '—'],
                  ['Policy action', selectedTx.action || '—'],
                  ['Reviewer outcome', selectedTx.reviewer_outcome || 'Pending'],
                ].map(([label, value]) => (
                  <div key={label} className="flex justify-between gap-4">
                    <span>{label}</span>
                    <span className="truncate font-mono text-text-primary">{value}</span>
                  </div>
                ))}
              </div>
            </div>

            {selectedTx.input_features && (
              <div className="space-y-2">
                <h4 className="eyebrow px-1">Input features</h4>
                <pre className="panel max-h-48 overflow-x-auto p-4 font-mono text-[11px] text-text-primary">
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
