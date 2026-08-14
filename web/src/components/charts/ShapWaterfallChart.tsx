import React from 'react';
import { EChartBase } from './EChartBase';
import type { EChartsOption } from 'echarts';
import type { ShapFeature } from '../../lib/types';

interface ShapWaterfallChartProps {
  features: ShapFeature[];
  height?: string | number;
}

export const ShapWaterfallChart: React.FC<ShapWaterfallChartProps> = ({
  features,
  height = '320px',
}) => {
  // Sort features by absolute contribution descending (top 10)
  const sorted = [...features]
    .sort((a, b) => Math.abs(b.contribution) - Math.abs(a.contribution))
    .slice(0, 8)
    .reverse();

  const labels = sorted.map((f) => f.feature);
  const values = sorted.map((f) => Math.round(f.contribution * 1000) / 1000);

  const option: EChartsOption = {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params: any) => {
        const item = params[0];
        const val = item.value;
        const color = val >= 0 ? '#F43F5E' : '#10B981';
        const dir = val >= 0 ? 'Increases Risk (Fraud Driver)' : 'Decreases Risk (Safe Signal)';
        return `<div class="font-mono text-xs">
          <div class="font-bold text-text-primary mb-1">${item.name}</div>
          <div style="color: ${color}">Contribution: ${val > 0 ? '+' : ''}${val}</div>
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
        fontFamily: 'JetBrains Mono',
        fontSize: 10,
        color: '#9CA3AF',
        formatter: '{value}',
      },
      splitLine: {
        lineStyle: {
          color: 'rgba(148, 163, 184, 0.1)',
        },
      },
    },
    yAxis: {
      type: 'category',
      data: labels,
      axisLabel: {
        fontFamily: 'JetBrains Mono',
        fontSize: 11,
        color: '#E6E8EE',
      },
      axisLine: {
        lineStyle: {
          color: '#222634',
        },
      },
    },
    series: [
      {
        name: 'SHAP Attribution',
        type: 'bar',
        data: values.map((val) => ({
          value: val,
          itemStyle: {
            color: val >= 0 ? '#F43F5E' : '#10B981', // Crimson vs Emerald
            borderRadius: val >= 0 ? [0, 4, 4, 0] : [4, 0, 0, 4],
          },
        })),
        barWidth: '60%',
      },
    ],
  };

  return <EChartBase option={option} height={height} />;
};
