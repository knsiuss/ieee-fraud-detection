import React from 'react';
import { EChartBase } from './EChartBase';
import type { EChartsOption } from 'echarts';
import type { ShapFeature } from '../../lib/types';
import { useThemeStore } from '../../stores/useThemeStore';

interface ShapWaterfallChartProps {
  features: ShapFeature[];
  height?: string | number;
}

export const ShapWaterfallChart: React.FC<ShapWaterfallChartProps> = ({
  features,
  height = '280px',
}) => {
  const theme = useThemeStore((s) => s.theme);
  const isDark = theme === 'dark';

  const approveColor = isDark ? '#4F7A5C' : '#3B5A44';
  const blockColor = isDark ? '#B23B2E' : '#A83A2E';
  const neutralColor = isDark ? '#A8A49A' : '#6E6A62';

  // Sort features by absolute contribution descending (top 8)
  const sorted = [...features]
    .sort((a, b) => Math.abs(b.contribution) - Math.abs(a.contribution))
    .slice(0, 8)
    .reverse();

  const labels = sorted.map((f) => f.feature);
  const values = sorted.map((f) => Math.round(f.contribution * 1000) / 1000);

  const option: EChartsOption = {
    animationDuration: 200,
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params: any) => {
        const item = params[0];
        const val = item.value;
        const color = val >= 0 ? blockColor : approveColor;
        const dir = val >= 0 ? 'Increases Risk (Fraud Driver)' : 'Decreases Risk (Safe Signal)';
        return `<div class="font-mono text-xs">
          <div class="font-bold mb-1 border-b border-border-subtle pb-1">${item.name}</div>
          <div style="color: ${color}" class="font-bold">Contribution: ${val > 0 ? '+' : ''}${val}</div>
          <div class="text-[11px] text-text-muted mt-0.5">${dir}</div>
        </div>`;
      },
    },
    grid: {
      left: '3%',
      right: '8%',
      bottom: '3%',
      top: '5%',
      containLabel: true,
    },
    xAxis: {
      type: 'value',
      axisLabel: {
        fontFamily: 'IBM Plex Mono, JetBrains Mono',
        fontSize: 10,
        color: neutralColor,
        formatter: '{value}',
      },
      splitLine: {
        lineStyle: {
          color: isDark ? 'rgba(230, 227, 218, 0.05)' : 'rgba(110, 106, 98, 0.08)',
          type: 'dashed',
        },
      },
    },
    yAxis: {
      type: 'category',
      data: labels,
      axisLabel: {
        fontFamily: 'IBM Plex Mono, JetBrains Mono',
        fontSize: 11,
        color: isDark ? '#F6F4EF' : '#17161A',
      },
      axisLine: {
        lineStyle: {
          color: isDark ? 'rgba(230, 227, 218, 0.10)' : '#DCD8CE',
        },
      },
      axisTick: { show: false },
    },
    series: [
      {
        name: 'SHAP Attribution',
        type: 'bar',
        data: values.map((val) => ({
          value: val,
          itemStyle: {
            color: val >= 0 ? blockColor : approveColor,
            borderRadius: [2, 2, 2, 2],
          },
        })),
        barWidth: '50%',
      },
    ],
  };

  return <EChartBase option={option} height={height} />;
};
