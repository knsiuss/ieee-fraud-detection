import React from 'react';

export interface TabItem<T extends string = string> {
  id: T;
  label: string;
  count?: number | string;
  badge?: string;
  icon?: React.ReactNode;
}

interface SegmentedTabsProps<T extends string = string> {
  tabs: TabItem<T>[];
  activeTab: T;
  onChange: (id: T) => void;
  size?: 'sm' | 'md';
}

export function SegmentedTabs<T extends string = string>({
  tabs,
  activeTab,
  onChange,
  size = 'md',
}: SegmentedTabsProps<T>) {
  return (
    <div className="inline-flex items-center gap-1 bg-surface-2/80 backdrop-blur-xl p-1 rounded-full border border-border-subtle shadow-inner">
      {tabs.map((tab) => {
        const isActive = activeTab === tab.id;
        const paddingClass = size === 'sm' ? 'px-3 py-1 text-xs' : 'px-4 py-1.5 text-xs';

        return (
          <button
            key={tab.id}
            onClick={() => onChange(tab.id)}
            className={`btn-interactive relative flex items-center gap-2 rounded-full font-medium transition-all duration-200 ${paddingClass} ${
              isActive
                ? 'bg-surface-1 text-text-primary shadow-sm border border-border-highlight font-semibold scale-[1.02]'
                : 'text-text-secondary hover:text-text-primary hover:bg-surface-hover/50'
            }`}
          >
            {tab.icon && <span className={`text-xs ${isActive ? 'text-apple-blue' : 'opacity-70'}`}>{tab.icon}</span>}
            <span className="font-sans">{tab.label}</span>

            {tab.count !== undefined && (
              <span
                className={`font-mono text-[10px] px-2 py-0.5 rounded-full font-semibold transition-colors ${
                  isActive
                    ? 'bg-surface-2 text-text-primary border border-border-subtle'
                    : 'bg-surface-1/60 text-text-muted'
                }`}
              >
                {tab.count}
              </span>
            )}

            {tab.badge && (
              <span className="bg-status-review/15 text-status-review border border-status-review/30 text-[10px] font-sans px-2 py-0.5 rounded-full font-semibold">
                {tab.badge}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
