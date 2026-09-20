import React, { useEffect, useRef } from 'react';
import * as echarts from 'echarts';
import type { ChartBlock } from '../types';

interface EChartRendererProps {
  block: ChartBlock;
}

export const EChartRenderer: React.FC<EChartRendererProps> = ({ block }) => {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    if (!chartRef.current) return;

    // Initialize ECharts instance
    if (!chartInstance.current) {
      chartInstance.current = echarts.init(chartRef.current);
    }

    const chart = chartInstance.current;

    // Build standard ECharts options from block
    let options: echarts.EChartsOption = {};

    if (block.option && Object.keys(block.option).length > 0) {
      options = {
        backgroundColor: 'transparent',
        textStyle: { fontFamily: 'Inter, system-ui, sans-serif' },
        ...block.option,
      };
    } else {
      // Default visualization fallback generated strictly from tool data
      const dataItems = Array.isArray(block.data) ? block.data : [];
      const categories = dataItems.map((d: any) => d.name || d.label || String(d[0] || ''));
      const values = dataItems.map((d: any) => (typeof d.value === 'number' ? d.value : d[1] || 0));

      options = {
        backgroundColor: 'transparent',
        title: {
          text: block.title,
          textStyle: { color: '#94a3b8', fontSize: 13, fontWeight: 500 },
          left: 'left',
        },
        tooltip: {
          trigger: 'axis',
          backgroundColor: '#0f172a',
          borderColor: '#334155',
          textStyle: { color: '#f8fafc', fontSize: 12 },
        },
        grid: { left: '4%', right: '4%', bottom: '8%', top: '16%', containLabel: true },
        xAxis: {
          type: 'category',
          data: categories,
          axisLine: { lineStyle: { color: '#334155' } },
          axisLabel: { color: '#94a3b8', fontSize: 11, interval: 0, rotate: categories.length > 5 ? 25 : 0 },
        },
        yAxis: {
          type: 'value',
          axisLine: { lineStyle: { color: '#334155' } },
          splitLine: { lineStyle: { color: '#1e293b' } },
          axisLabel: { color: '#94a3b8', fontSize: 11 },
        },
        series: [
          {
            name: block.title,
            type: block.chart_type === 'line' ? 'line' : 'bar',
            data: values,
            itemStyle: { color: '#0284c7', borderRadius: [4, 4, 0, 0] },
          },
        ],
      };
    }

    chart.setOption(options, true);

    const handleResize = () => {
      chart.resize();
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.dispose();
      chartInstance.current = null;
    };
  }, [block]);

  return (
    <div className="my-4 p-4 rounded-md border border-slate-800 bg-slate-900/60">
      <div className="text-xs font-medium text-slate-400 mb-2">{block.title}</div>
      <div ref={chartRef} className="w-full h-64" />
    </div>
  );
};
