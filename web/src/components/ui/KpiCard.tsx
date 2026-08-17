import React from 'react';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

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

export const KpiCard: React.FC<KpiCardProps> = ({
  title,
  value,
  subtitle,
  trend,
  icon,
}) => {
  return (
    <div className="panel panel-hover p-4 flex flex-col justify-between">
      <div className="flex items-center justify-between gap-2">
        <span className="text-[11px] font-mono font-medium uppercase tracking-wider text-text-secondary">
          {title}
        </span>
        {icon && (
          <span className="w-7 h-7 rounded-full bg-surface-2 flex items-center justify-center text-text-secondary shrink-0">
            {icon}
          </span>
        )}
      </div>

      <div className="mt-2.5 flex items-baseline justify-between gap-2">
        <span className="text-[26px] font-bold font-mono tracking-tight text-text-primary tabular-nums leading-none">
          {value}
        </span>

        {trend && (
          <div
            className={`inline-flex items-center gap-1 text-[11px] font-mono font-semibold px-2 py-1 rounded-full ${
              trend.direction === 'up'
                ? 'text-status-approve bg-status-approve-soft'
                : trend.direction === 'down'
                ? 'text-status-block bg-status-block-soft'
                : 'text-text-muted bg-surface-2'
            }`}
          >
            {trend.direction === 'up' && <TrendingUp className="w-3 h-3" />}
            {trend.direction === 'down' && <TrendingDown className="w-3 h-3" />}
            {trend.direction === 'neutral' && <Minus className="w-3 h-3" />}
            <span>{trend.value}</span>
          </div>
        )}
      </div>

      {(subtitle || trend?.label) && (
        <div className="mt-1.5 text-[11px] font-mono text-text-muted truncate">
          {subtitle || trend?.label}
        </div>
      )}
    </div>
  );
};
