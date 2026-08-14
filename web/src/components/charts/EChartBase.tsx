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
  const textColor = isDark ? '#A8A49A' : '#6E6A62';
  const borderColor = isDark ? 'rgba(230, 227, 218, 0.10)' : '#DCD8CE';
  const splitLineColor = isDark ? 'rgba(230, 227, 218, 0.05)' : 'rgba(110, 106, 98, 0.08)';

  const mergedOption: EChartsOption = {
    backgroundColor: 'transparent',
    textStyle: {
      fontFamily: 'IBM Plex Mono, JetBrains Mono, monospace',
      color: textColor,
    },
    tooltip: {
      backgroundColor: isDark ? '#26252B' : '#FFFFFF',
      borderColor: borderColor,
      borderWidth: 1,
      padding: [8, 12],
      textStyle: {
        color: isDark ? '#F6F4EF' : '#17161A',
        fontSize: 11,
        fontFamily: 'IBM Plex Mono, JetBrains Mono, monospace',
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
