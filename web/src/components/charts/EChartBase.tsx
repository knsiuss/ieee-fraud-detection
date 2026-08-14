import React, { useRef, useEffect } from 'react';
import ReactEChartsCore from 'echarts-for-react/lib/core';
import type { EChartsOption } from 'echarts';
import echarts from '../../lib/echarts-core';
import { useThemeStore } from '../../stores/useThemeStore';

interface EChartBaseProps {
  option: EChartsOption;
  height?: string | number;
  className?: string;
  onEvents?: Record<string, (e: any) => void>;
}

export const EChartBase: React.FC<EChartBaseProps> = ({
  option,
  height = '300px',
  className = '',
  onEvents,
}) => {
  const theme = useThemeStore((s) => s.theme);
  const chartRef = useRef<ReactEChartsCore>(null);

  useEffect(() => {
    if (chartRef.current) {
      chartRef.current.getEchartsInstance()?.resize();
    }
  }, [theme]);

  // Merge default theme styling (Dark vs Light)
  const isDark = theme === 'dark';
  const textColor = isDark ? '#9CA3AF' : '#4B5563';
  const borderColor = isDark ? '#222634' : '#E5E7EB';
  const splitLineColor = isDark ? 'rgba(148, 163, 184, 0.08)' : 'rgba(100, 116, 139, 0.12)';

  const mergedOption: EChartsOption = {
    backgroundColor: 'transparent',
    textStyle: {
      fontFamily: 'JetBrains Mono, SF Mono, Geist, sans-serif',
      color: textColor,
    },
    tooltip: {
      backgroundColor: isDark ? '#171A24' : '#FFFFFF',
      borderColor: borderColor,
      borderWidth: 1,
      textStyle: {
        color: isDark ? '#E6E8EE' : '#111827',
        fontSize: 12,
        fontFamily: 'JetBrains Mono, monospace',
      },
      ...option.tooltip,
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      top: '12%',
      containLabel: true,
      borderColor: splitLineColor,
      ...((option.grid as any) || {}),
    },
    ...option,
  };

  return (
    <div className={`w-full overflow-hidden ${className}`} style={{ height }}>
      <ReactEChartsCore
        ref={chartRef}
        echarts={echarts}
        option={mergedOption}
        style={{ height: '100%', width: '100%' }}
        onEvents={onEvents}
        notMerge={true}
        lazyUpdate={true}
      />
    </div>
  );
};
