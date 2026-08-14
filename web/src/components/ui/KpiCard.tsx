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
  accent = 'teal',
  icon,
  pulse = false,
}) => {
  const accentColors = {
    teal: 'border-l-accent-teal hover:border-accent-teal/40',
    cyan: 'border-l-accent-cyan hover:border-accent-cyan/40',
    emerald: 'border-l-status-approve hover:border-status-approve/40',
    amber: 'border-l-status-review hover:border-status-review/40',
    crimson: 'border-l-status-block hover:border-status-block/40',
  };

  return (
    <div
      className={`relative bg-surface-1 border border-border-subtle border-l-4 ${accentColors[accent]} rounded-lg p-4 transition-all duration-200 hover:bg-surface-2 flex flex-col justify-between`}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-medium uppercase tracking-wider text-text-secondary">
          {title}
        </span>
        <div className="flex items-center gap-2">
          {pulse && (
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-accent-teal opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-accent-teal"></span>
            </span>
          )}
          {icon && <span className="text-text-muted">{icon}</span>}
        </div>
      </div>

      <div className="mt-2 flex items-baseline justify-between gap-2">
        <span className="text-2xl font-bold font-mono tracking-tight text-text-primary">
          {value}
        </span>

        {trend && (
          <div
            className={`inline-flex items-center gap-1 text-xs font-mono font-medium ${
              trend.direction === 'up'
                ? 'text-status-approve'
                : trend.direction === 'down'
                ? 'text-status-block'
                : 'text-text-muted'
            }`}
          >
            {trend.direction === 'up' && <TrendingUp className="w-3.5 h-3.5" />}
            {trend.direction === 'down' && <TrendingDown className="w-3.5 h-3.5" />}
            {trend.direction === 'neutral' && <Minus className="w-3.5 h-3.5" />}
            <span>{trend.value}</span>
          </div>
        )}
      </div>

      {(subtitle || trend?.label) && (
        <div className="mt-1 text-[11px] text-text-muted truncate">
          {subtitle || trend?.label}
        </div>
      )}
    </div>
  );
};
