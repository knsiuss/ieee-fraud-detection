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
    <div className="flex items-center gap-1 bg-surface-1 border border-border-subtle p-1 rounded-lg">
      {tabs.map((tab) => {
        const isActive = activeTab === tab.id;
        const paddingClass = size === 'sm' ? 'px-3 py-1.5 text-xs' : 'px-4 py-2 text-xs font-medium';

        return (
          <button
            key={tab.id}
            onClick={() => onChange(tab.id)}
            className={`relative flex items-center gap-2 rounded-md transition-all duration-150 ${paddingClass} ${
              isActive
                ? 'bg-surface-2 text-text-primary shadow-xs font-semibold'
                : 'text-text-secondary hover:text-text-primary hover:bg-surface-hover/50'
            }`}
          >
            {tab.icon && <span className="opacity-80">{tab.icon}</span>}
            <span>{tab.label}</span>

            {tab.count !== undefined && (
              <span
                className={`font-mono text-[10px] px-1.5 py-0.2 rounded-full ${
                  isActive
                    ? 'bg-accent-teal/20 text-accent-teal'
                    : 'bg-surface-hover text-text-muted'
                }`}
              >
                {tab.count}
              </span>
            )}

            {tab.badge && (
              <span className="bg-status-review/20 text-status-review text-[10px] font-mono px-1.5 py-0.5 rounded font-bold">
                {tab.badge}
              </span>
            )}

            {isActive && (
              <span className="absolute bottom-0 left-2 right-2 h-[2px] bg-accent-teal rounded-full" />
            )}
          </button>
        );
      })}
    </div>
  );
}
