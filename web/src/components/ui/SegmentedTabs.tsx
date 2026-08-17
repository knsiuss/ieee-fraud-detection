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
    <div className="flex items-center gap-1 panel p-1">
      {tabs.map((tab) => {
        const isActive = activeTab === tab.id;
        const paddingClass = size === 'sm' ? 'px-2.5 py-1 text-xs' : 'px-3.5 py-1.5 text-xs';

        return (
          <button
            key={tab.id}
            onClick={() => onChange(tab.id)}
            className={`btn-interactive relative flex items-center gap-1.5 rounded-full font-mono transition-colors ${paddingClass} ${
              isActive
                ? 'bg-surface-2 text-text-primary shadow-sm font-bold'
                : 'text-text-secondary hover:text-text-primary hover:bg-surface-hover'
            }`}
          >
            {tab.icon && <span className="opacity-70">{tab.icon}</span>}
            <span>{tab.label}</span>

            {tab.count !== undefined && (
              <span
                className={`font-mono text-[10px] px-2 py-0.5 rounded-full ${
                  isActive
                    ? 'bg-surface-1 text-text-primary font-bold'
                    : 'bg-surface-2 text-text-muted'
                }`}
              >
                {tab.count}
              </span>
            )}

            {tab.badge && (
              <span className="bg-status-review-soft text-status-review text-[10px] font-mono px-2 py-0.5 rounded-full font-bold">
                {tab.badge}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
