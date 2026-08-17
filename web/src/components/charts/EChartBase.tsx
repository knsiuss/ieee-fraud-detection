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
  height = '280px',
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

  const isDark = theme === 'dark';
  const textColor = isDark ? '#9898A0' : '#6E6E73';
  const borderColor = isDark ? 'rgba(255, 255, 255, 0.12)' : 'rgba(0, 0, 0, 0.10)';
  const splitLineColor = isDark ? 'rgba(255, 255, 255, 0.05)' : 'rgba(0, 0, 0, 0.05)';

  const mergedOption: EChartsOption = {
    backgroundColor: 'transparent',
    textStyle: {
      fontFamily: '-apple-system, BlinkMacSystemFont, "SF Pro Text", "Inter", sans-serif',
      color: textColor,
    },
    tooltip: {
      backgroundColor: isDark ? 'rgba(30, 30, 38, 0.88)' : 'rgba(255, 255, 255, 0.92)',
      borderColor: borderColor,
      borderWidth: 1,
      padding: [10, 14],
      borderRadius: 14,
      shadowColor: 'rgba(0, 0, 0, 0.25)',
      shadowBlur: 16,
      textStyle: {
        color: isDark ? '#F5F5F7' : '#1D1D1F',
        fontSize: 12,
        fontFamily: '-apple-system, BlinkMacSystemFont, "SF Pro Text", "Inter", monospace',
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
      />
    </div>
  );
};
