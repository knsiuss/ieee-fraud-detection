import React, { useEffect, useRef } from 'react';
import cytoscape from 'cytoscape';
import { useThemeStore } from '../../stores/useThemeStore';

interface FraudRingGraphProps {
  height?: string | number;
  onNodeClick?: (nodeId: string, nodeType: string) => void;
}

export const FraudRingGraph: React.FC<FraudRingGraphProps> = ({
  height = '420px',
  onNodeClick,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<cytoscape.Core | null>(null);
  const theme = useThemeStore((s) => s.theme);

  useEffect(() => {
    if (!containerRef.current) return;

    const isDark = theme === 'dark';
    const textColor = isDark ? '#F5F5F7' : '#1D1D1F';
    const edgeColor = isDark ? 'rgba(255, 255, 255, 0.12)' : 'rgba(0, 0, 0, 0.10)';
    const blockColor = isDark ? '#FF453A' : '#D70015';
    const reviewColor = isDark ? '#FF9F0A' : '#C97500';
    const approveColor = isDark ? '#30D158' : '#248A3D';
    const surfaceBg = isDark ? 'rgba(38, 38, 48, 0.8)' : 'rgba(240, 240, 246, 0.9)';

    const cy = cytoscape({
      container: containerRef.current,
      style: [
        {
          selector: 'node',
          style: {
            label: 'data(label)',
            color: textColor,
            'font-family': '-apple-system, BlinkMacSystemFont, "SF Pro Text", "Inter", sans-serif',
            'font-size': '11px',
            'text-valign': 'bottom',
            'text-margin-y': 6,
            width: 32,
            height: 32,
            'border-width': 2,
            'border-color': 'data(borderColor)',
            'background-color': 'data(bgColor)',
          },
        },
        {
          selector: 'node[type = "transaction"]',
          style: {
            shape: 'round-rectangle',
            width: 42,
            height: 28,
          },
        },
        {
          selector: 'node[type = "card"]',
          style: {
            shape: 'diamond',
            width: 32,
            height: 32,
          },
        },
        {
          selector: 'edge',
          style: {
            width: 1.5,
            'line-color': edgeColor,
            'curve-style': 'bezier',
            'target-arrow-shape': 'none',
            opacity: 0.8,
          },
        },
        {
          selector: 'edge[fraud = "true"]',
          style: {
            'line-color': blockColor,
            width: 2,
            'line-style': 'dashed',
            opacity: 0.95,
          },
        },
        {
          selector: ':selected',
          style: {
            'border-color': textColor,
            'border-width': 3,
          },
        },
      ],
      elements: [
        // Seed cluster 1: Card syndicate
        { data: { id: 'c1', label: 'Card •••• 4912', type: 'card', bgColor: surfaceBg, borderColor: blockColor } },
        { data: { id: 'tx1', label: 'TX-98421 ($1.4k)', type: 'transaction', bgColor: surfaceBg, borderColor: blockColor } },
        { data: { id: 'tx2', label: 'TX-98422 ($850)', type: 'transaction', bgColor: surfaceBg, borderColor: blockColor } },
        { data: { id: 'ip1', label: 'IP 185.220.101.5 (Tor)', type: 'ip', bgColor: surfaceBg, borderColor: reviewColor } },
        { data: { id: 'em1', label: 'tempmail-99@xyz.org', type: 'email', bgColor: surfaceBg, borderColor: blockColor } },
        
        // Seed cluster 2: Identity proxy syndicate
        { data: { id: 'c2', label: 'Card •••• 8821', type: 'card', bgColor: surfaceBg, borderColor: reviewColor } },
        { data: { id: 'tx3', label: 'TX-98430 ($420)', type: 'transaction', bgColor: surfaceBg, borderColor: reviewColor } },
        { data: { id: 'dev1', label: 'Device: Linux/Chrome Headless', type: 'device', bgColor: surfaceBg, borderColor: textColor } },
        { data: { id: 'tx4', label: 'TX-98435 ($310)', type: 'transaction', bgColor: surfaceBg, borderColor: approveColor } },

        // Edges
        { data: { id: 'e1', source: 'tx1', target: 'c1', fraud: 'true' } },
        { data: { id: 'e2', source: 'tx2', target: 'c1', fraud: 'true' } },
        { data: { id: 'e3', source: 'tx1', target: 'ip1', fraud: 'true' } },
        { data: { id: 'e4', source: 'tx2', target: 'em1', fraud: 'true' } },
        { data: { id: 'e5', source: 'tx3', target: 'c2' } },
        { data: { id: 'e6', source: 'tx3', target: 'dev1' } },
        { data: { id: 'e7', source: 'tx4', target: 'dev1' } },
        { data: { id: 'e8', source: 'ip1', target: 'tx3', fraud: 'true' } },
      ],
      layout: {
        name: 'cose',
        animate: false,
        padding: 28,
        nodeRepulsion: () => 4500,
        idealEdgeLength: () => 70,
      },
    });

    cy.on('tap', 'node', (evt) => {
      const node = evt.target;
      if (onNodeClick) {
        onNodeClick(node.id(), node.data('type'));
      }
    });

    cyRef.current = cy;

    return () => {
      cy.destroy();
    };
  }, [theme, onNodeClick]);

  return (
    <div className="relative w-full panel rounded-2xl overflow-hidden border border-border-subtle shadow-soft">
      <div className="absolute top-3.5 left-3.5 z-10 flex items-center gap-2 bg-surface-2/80 backdrop-blur-md px-3 py-1.5 rounded-full border border-border-subtle text-xs font-sans text-text-secondary shadow-sm">
        <span className="w-2 h-2 rounded-full bg-status-block animate-pulse"></span>
        <span className="font-medium">Syndicate Cluster Entity Graph</span>
      </div>
      <div ref={containerRef} style={{ height, width: '100%' }} />
    </div>
  );
};
