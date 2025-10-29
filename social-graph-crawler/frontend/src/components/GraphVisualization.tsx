import React, { useEffect, useRef } from 'react';
import * as d3 from 'd3';
import { GraphData, Node, Edge } from '../services/api';

interface GraphVisualizationProps {
  data: GraphData | null;
  onNodeClick?: (node: Node) => void;
  width?: number;
  height?: number;
}

interface D3Node extends Node {
  x?: number;
  y?: number;
  fx?: number | null;
  fy?: number | null;
  vx?: number;
  vy?: number;
}

export const GraphVisualization: React.FC<GraphVisualizationProps> = ({
  data,
  onNodeClick,
  width = 1200,
  height = 800,
}) => {
  const svgRef = useRef<SVGSVGElement>(null);
  const simulationRef = useRef<d3.Simulation<D3Node, Edge> | null>(null);

  useEffect(() => {
    if (!data || !svgRef.current) return;

    // Clear previous visualization
    d3.select(svgRef.current).selectAll('*').remove();

    const svg = d3.select(svgRef.current);
    
    // Create container group for zoom/pan
    const container = svg.append('g');

    // Define arrow markers for edges
    svg.append('defs').selectAll('marker')
      .data(['end'])
      .enter().append('marker')
      .attr('id', String)
      .attr('viewBox', '0 -5 10 10')
      .attr('refX', 20)
      .attr('refY', 0)
      .attr('markerWidth', 6)
      .attr('markerHeight', 6)
      .attr('orient', 'auto')
      .append('path')
      .attr('d', 'M0,-5L10,0L0,5')
      .attr('fill', '#999');

    // Create force simulation
    const simulation = d3.forceSimulation<D3Node>(data.nodes as D3Node[])
      .force('link', d3.forceLink<D3Node, Edge>(data.edges)
        .id((d: any) => d.id)
        .distance(100))
      .force('charge', d3.forceManyBody().strength(-300))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collision', d3.forceCollide().radius(30));

    simulationRef.current = simulation;

    // Draw edges
    const link = container.append('g')
      .selectAll('line')
      .data(data.edges)
      .enter().append('line')
      .attr('class', 'link')
      .attr('stroke', '#999')
      .attr('stroke-opacity', 0.6)
      .attr('stroke-width', (d: Edge) => Math.sqrt(d.weight) * 2)
      .attr('marker-end', 'url(#end)');

    // Draw nodes
    const node = container.append('g')
      .selectAll('circle')
      .data(data.nodes)
      .enter().append('circle')
      .attr('class', 'node')
      .attr('r', 8)
      .attr('fill', (d: Node) => getNodeColor(d.source))
      .attr('stroke', '#fff')
      .attr('stroke-width', 2)
      .on('click', (event, d: Node) => {
        event.stopPropagation();
        if (onNodeClick) onNodeClick(d);
      })
      .call(drag(simulation) as any);

    // Add labels
    const label = container.append('g')
      .selectAll('text')
      .data(data.nodes)
      .enter().append('text')
      .text((d: Node) => d.display_name)
      .attr('font-size', 10)
      .attr('dx', 12)
      .attr('dy', 4);

    // Update positions on simulation tick
    simulation.on('tick', () => {
      link
        .attr('x1', (d: any) => d.source.x)
        .attr('y1', (d: any) => d.source.y)
        .attr('x2', (d: any) => d.target.x)
        .attr('y2', (d: any) => d.target.y);

      node
        .attr('cx', (d: any) => d.x)
        .attr('cy', (d: any) => d.y);

      label
        .attr('x', (d: any) => d.x)
        .attr('y', (d: any) => d.y);
    });

    // Add zoom behavior
    const zoom = d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.1, 10])
      .on('zoom', (event) => {
        container.attr('transform', event.transform);
      });

    svg.call(zoom as any);

    // Cleanup
    return () => {
      simulation.stop();
    };
  }, [data, width, height, onNodeClick]);

  function drag(simulation: d3.Simulation<D3Node, Edge>) {
    function dragstarted(event: any) {
      if (!event.active) simulation.alphaTarget(0.3).restart();
      event.subject.fx = event.subject.x;
      event.subject.fy = event.subject.y;
    }

    function dragged(event: any) {
      event.subject.fx = event.x;
      event.subject.fy = event.y;
    }

    function dragended(event: any) {
      if (!event.active) simulation.alphaTarget(0);
      event.subject.fx = null;
      event.subject.fy = null;
    }

    return d3.drag()
      .on('start', dragstarted)
      .on('drag', dragged)
      .on('end', dragended);
  }

  function getNodeColor(source: string): string {
    const colors: Record<string, string> = {
      reddit: '#FF4500',
      github: '#333333',
      wikipedia: '#000000',
    };
    return colors[source] || '#69b3a2';
  }

  return (
    <div className="graph-container">
      <svg
        ref={svgRef}
        width={width}
        height={height}
        style={{ border: '1px solid #ddd', background: '#fff' }}
      />
    </div>
  );
};

export default GraphVisualization;
