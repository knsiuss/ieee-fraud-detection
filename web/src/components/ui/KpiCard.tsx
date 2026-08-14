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
  const accentBorders = {
    teal: 'border-l-accent-teal hover:border-l-accent-teal hover:shadow-[0_4px_20px_-4px_rgba(20,184,166,0.2)]',
    cyan: 'border-l-accent-cyan hover:border-l-accent-cyan hover:shadow-[0_4px_20px_-4px_rgba(6,182,212,0.2)]',
    emerald: 'border-l-status-approve hover:border-l-status-approve hover:shadow-[0_4px_20px_-4px_rgba(16,185,129,0.2)]',
    amber: 'border-l-status-review hover:border-l-status-review hover:shadow-[0_4px_20px_-4px_rgba(245,158,11,0.2)]',
    crimson: 'border-l-status-block hover:border-l-status-block hover:shadow-[0_4px_20px_-4px_rgba(244,63,94,0.2)]',
  };

  return (
    <div
      className={`relative bg-surface-1/90 backdrop-blur-sm border border-border-subtle border-l-[3px] ${accentBorders[accent]} rounded-lg p-4 transition-all duration-200 ease-out hover:-translate-y-0.5 hover:bg-surface-2 flex flex-col justify-between shadow-xs group`}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="text-[11px] font-semibold uppercase tracking-wider text-text-secondary group-hover:text-text-primary transition-colors">
          {title}
        </span>
        <div className="flex items-center gap-2">
          {pulse && (
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-accent-teal opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-accent-teal"></span>
            </span>
          )}
          {icon && (
            <span className="text-text-muted group-hover:text-text-secondary transition-colors">
              {icon}
            </span>
          )}
        </div>
      </div>

      <div className="mt-2.5 flex items-baseline justify-between gap-2">
        <span className="text-2xl font-bold font-mono tracking-tight text-text-primary">
          {value}
        </span>

        {trend && (
          <div
            className={`inline-flex items-center gap-1 text-xs font-mono font-medium px-1.5 py-0.5 rounded ${
              trend.direction === 'up'
                ? 'text-status-approve bg-status-approve/10'
                : trend.direction === 'down'
                ? 'text-status-block bg-status-block/10'
                : 'text-text-muted bg-surface-hover'
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
        <div className="mt-1.5 text-[11px] text-text-muted truncate font-mono">
          {subtitle || trend?.label}
        </div>
      )}
    </div>
  );
};
