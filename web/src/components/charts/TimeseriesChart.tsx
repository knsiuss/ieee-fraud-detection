import React from 'react';
import { EChartBase } from './EChartBase';
import type { EChartsOption } from 'echarts';
import type { TimeseriesBucket } from '../../lib/types';
import { useThemeStore } from '../../stores/useThemeStore';

interface TimeseriesChartProps {
  data: TimeseriesBucket[];
  height?: string | number;
  showAmount?: boolean;
}

export const TimeseriesChart: React.FC<TimeseriesChartProps> = ({
  data,
  height = '300px',
  showAmount = false,
}) => {
  const theme = useThemeStore((s) => s.theme);
  const isDark = theme === 'dark';

  const timestamps = data.map((d) => {
    try {
      const date = new Date(d.timestamp);
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch {
      return d.timestamp;
    }
  });

  const totals = data.map((d) => d.total);
  const approved = data.map((d) => d.approved);
  const reviewed = data.map((d) => d.reviewed);
  const declined = data.map((d) => d.declined);
  const amounts = data.map((d) => d.amount_sum);

  const approveColor = isDark ? '#4F7A5C' : '#3B5A44';
  const reviewColor = isDark ? '#B8863A' : '#A87B34';
  const blockColor = isDark ? '#B23B2E' : '#A83A2E';
  const neutralColor = isDark ? '#A8A49A' : '#6E6A62';

  const option: EChartsOption = {
    animationDuration: 300,
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'line',
        lineStyle: {
          color: isDark ? 'rgba(230, 227, 218, 0.2)' : 'rgba(110, 106, 98, 0.3)',
          width: 1,
          type: 'dashed',
        },
      },
      formatter: (params: any) => {
        if (!params || !params.length) return '';
        const idx = params[0].dataIndex;
        const bucket = data[idx];
        return `<div class="font-mono text-xs space-y-1">
          <div class="font-bold border-b border-border-subtle pb-1 mb-1 flex items-center justify-between gap-4">
            <span>${timestamps[idx]} (Window)</span>
            <span>${bucket.total} tx</span>
          </div>
          <div class="flex justify-between gap-6" style="color: ${approveColor}">
            <span>Auto-Approved:</span>
            <b>${bucket.approved}</b>
          </div>
          <div class="flex justify-between gap-6" style="color: ${reviewColor}">
            <span>Review Queue:</span>
            <b>${bucket.reviewed}</b>
          </div>
          <div class="flex justify-between gap-6" style="color: ${blockColor}">
            <span>Declined:</span>
            <b>${bucket.declined}</b>
          </div>
          <div class="flex justify-between gap-6 pt-1 border-t border-border-subtle">
            <span>Evaluated GMV:</span>
            <b>$${bucket.amount_sum.toLocaleString()}</b>
          </div>
        </div>`;
      },
    },
    legend: {
      data: showAmount
        ? ['Transaction Volume', 'Evaluated GMV ($)', 'Declined (Fraud)']
        : ['Total Volume', 'Approved', 'Review', 'Declined'],
      textStyle: { color: neutralColor, fontSize: 11, fontFamily: 'IBM Plex Mono, JetBrains Mono' },
      top: 0,
      right: 10,
      icon: 'roundRect',
      itemWidth: 10,
      itemHeight: 3,
      itemGap: 14,
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '4%',
      top: '16%',
      containLabel: true,
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: timestamps,
      axisLabel: {
        color: neutralColor,
        fontSize: 10,
        fontFamily: 'IBM Plex Mono, JetBrains Mono',
      },
      axisLine: { lineStyle: { color: isDark ? 'rgba(230, 227, 218, 0.10)' : '#DCD8CE' } },
      axisTick: { show: false },
    },
    yAxis: [
      {
        type: 'value',
        name: 'Volume (tx)',
        nameTextStyle: { color: neutralColor, fontSize: 10, fontFamily: 'IBM Plex Mono, JetBrains Mono' },
        axisLabel: { color: neutralColor, fontSize: 10, fontFamily: 'IBM Plex Mono, JetBrains Mono' },
        splitLine: {
          lineStyle: {
            color: isDark ? 'rgba(230, 227, 218, 0.05)' : 'rgba(110, 106, 98, 0.08)',
            type: 'dashed',
          },
        },
      },
      ...(showAmount
        ? [
            {
              type: 'value' as const,
              name: 'GMV ($)',
              nameTextStyle: { color: neutralColor, fontSize: 10, fontFamily: 'IBM Plex Mono, JetBrains Mono' },
              axisLabel: {
                color: neutralColor,
                fontSize: 10,
                fontFamily: 'IBM Plex Mono, JetBrains Mono',
                formatter: '${value}',
              },
              splitLine: { show: false },
            },
          ]
        : []),
    ],
    series: showAmount
      ? [
          {
            name: 'Transaction Volume',
            type: 'line',
            smooth: 0.2,
            showSymbol: false,
            data: totals,
            itemStyle: { color: neutralColor },
            lineStyle: { width: 1.5, color: neutralColor },
          },
          {
            name: 'Evaluated GMV ($)',
            type: 'line',
            yAxisIndex: 1,
            smooth: 0.2,
            showSymbol: false,
            data: amounts,
            itemStyle: { color: approveColor },
            lineStyle: { width: 1.5, color: approveColor },
          },
          {
            name: 'Declined (Fraud)',
            type: 'bar',
            data: declined,
            itemStyle: {
              color: blockColor,
              borderRadius: [2, 2, 0, 0],
            },
            barWidth: '30%',
          },
        ]
      : [
          {
            name: 'Total Volume',
            type: 'line',
            smooth: 0.2,
            showSymbol: false,
            data: totals,
            itemStyle: { color: neutralColor },
            lineStyle: { width: 1.5, color: neutralColor },
          },
          {
            name: 'Approved',
            type: 'line',
            smooth: 0.2,
            showSymbol: false,
            data: approved,
            itemStyle: { color: approveColor },
            lineStyle: { width: 1.5, color: approveColor },
          },
          {
            name: 'Review',
            type: 'line',
            smooth: 0.2,
            showSymbol: false,
            data: reviewed,
            itemStyle: { color: reviewColor },
            lineStyle: { width: 1.5, color: reviewColor },
          },
          {
            name: 'Declined',
            type: 'line',
            smooth: 0.2,
            showSymbol: false,
            data: declined,
            itemStyle: { color: blockColor },
            lineStyle: { width: 1.5, color: blockColor },
          },
        ],
  };

  return <EChartBase option={option} height={height} />;
};
