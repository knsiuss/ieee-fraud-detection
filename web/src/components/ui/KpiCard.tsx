import React from 'react';

interface KpiCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  trend?: {
    value: string | number;
    direction: 'up' | 'down' | 'neutral';
    label?: string;
  };
  accent?: 'teal' | 'cyan' | 'emerald' | 'amber' | 'crimson';
  icon?: React.ReactNode;
  pulse?: boolean;
}

const TREND_STYLES: Record<'up' | 'down' | 'neutral', string> = {
  up: 'text-status-approve bg-status-approve/10',
  down: 'text-status-block bg-status-block/10',
  neutral: 'text-text-secondary bg-surface-2',
};

export const KpiCard: React.FC<KpiCardProps> = ({ title, value, subtitle, trend, icon }) => {
  return (
    <div className="panel px-4 py-3.5">
      <div className="flex items-center gap-1.5">
        <span className="eyebrow">{title}</span>
        {icon && <span className="text-text-muted">{icon}</span>}
      </div>

      <div className="mt-2.5 flex flex-wrap items-baseline gap-x-2 gap-y-1">
        <span className="font-mono text-[24px] font-semibold leading-none tracking-tight tabular-nums text-text-primary">
          {value}
        </span>
        {trend && (
          <span
            className={`rounded-md px-1.5 py-0.5 text-[10.5px] font-medium tabular-nums ${
              TREND_STYLES[trend.direction] ?? TREND_STYLES.neutral
            }`}
          >
            {trend.value}
          </span>
        )}
      </div>

      {(subtitle || trend?.label) && (
        <div className="mt-1.5 text-[11.5px] leading-snug text-text-muted">
          {subtitle || trend?.label}
        </div>
      )}
    </div>
  );
};
