import React from 'react';

export interface ScoreBarDriver {
  label: string;
  direction: 'fraud' | 'safe';
}

export interface ScoreBarThresholds {
  review_above?: number;
  decline_above?: number;
  auto_action_above?: number;
}

interface ScoreBarProps {
  probability: number; // 0.0 to 1.0
  topDriver?: ScoreBarDriver;
  thresholds?: ScoreBarThresholds;
  compact?: boolean;
  showPercentage?: boolean;
  className?: string;
}

export const ScoreBar: React.FC<ScoreBarProps> = ({
  probability,
  topDriver,
  thresholds = { review_above: 0.2, decline_above: 0.8 },
  compact = false,
  showPercentage = false,
  className = '',
}) => {
  const clampProb = Math.max(0, Math.min(1, probability));
  const pct = (clampProb * 100).toFixed(1);
  const rawNum = clampProb.toFixed(3);

  const revThresh = thresholds.review_above ?? 0.2;
  const decThresh = thresholds.decline_above ?? 0.8;

  // Decision zone color
  let fillColor = 'bg-status-approve';
  let textColor = 'text-status-approve';
  if (clampProb >= decThresh) {
    fillColor = 'bg-status-block';
    textColor = 'text-status-block';
  } else if (clampProb >= revThresh) {
    fillColor = 'bg-status-review';
    textColor = 'text-status-review';
  }

  return (
    <div className={`flex flex-col gap-1.5 font-sans ${className}`}>
      {/* Track & threshold markers */}
      <div className="relative h-1.5 w-full overflow-hidden rounded-full bg-surface-2 border border-border-subtle">
        {/* Threshold Markers */}
        <div
          className="absolute top-0 bottom-0 w-[1px] bg-border-highlight z-10"
          style={{ left: `${revThresh * 100}%` }}
          title={`Review threshold: ${revThresh}`}
        />
        <div
          className="absolute top-0 bottom-0 w-[1px] bg-border-highlight z-10"
          style={{ left: `${decThresh * 100}%` }}
          title={`Decline threshold: ${decThresh}`}
        />

        {/* Filled score */}
        <div
          className={`h-full rounded-full ${fillColor} transition-[width] duration-300`}
          style={{ width: `${Math.max(clampProb * 100, 1.5)}%` }}
        />
      </div>

      {/* Numerics + Driver Inline */}
      <div className="flex items-center justify-between text-[11px] leading-none">
        <div className="flex items-center gap-1.5 font-mono">
          <span className={`font-semibold tabular-nums ${textColor}`}>
            {showPercentage ? `${pct}%` : rawNum}
          </span>

          {topDriver && (
            <span className="text-text-secondary text-[11px] font-sans truncate flex items-center gap-0.5">
              <span className="text-text-muted">· {topDriver.label}</span>
              <span className={topDriver.direction === 'fraud' ? 'text-status-block' : 'text-status-approve'}>
                {topDriver.direction === 'fraud' ? '↑' : '↓'}
              </span>
            </span>
          )}
        </div>

        {!compact && (
          <span className="text-[10px] font-medium uppercase tracking-wider text-text-muted">
            {clampProb >= decThresh ? 'DECLINE' : clampProb >= revThresh ? 'REVIEW' : 'APPROVE'}
          </span>
        )}
      </div>
    </div>
  );
};
