import React, { useEffect, useRef, useState, useCallback } from 'react';
import * as d3 from 'd3';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Search,
  ZoomIn,
  ZoomOut,
  RotateCcw,
  Download,
  Filter,
  Settings,
  Info,
  Maximize,
} from 'lucide-react';
import { useToast } from '@/hooks/use-toast';

interface GraphNode {
  id: string;
  label: string;
  type: string;
  properties: Record<string, unknown>;
  x?: number;
  y?: number;
  fx?: number;
  fy?: number;
}

interface GraphLink {
  source: string | GraphNode;
  target: string | GraphNode;
  type: string;
  properties: Record<string, any>;
}

interface GraphData {
  nodes: GraphNode[];
  links: GraphLink[];
}

interface GraphVisualizationProps {
  data: GraphData;
  width?: number;
  height?: number;
  onNodeSelect?: (node: GraphNode) => void;
  onNodeDoubleClick?: (node: GraphNode) => void;
  className?: string;
}

const NODE_COLORS = {
  Document: '#3b82f6',
  Entity: '#10b981',
  Concept: '#8b5cf6',
  User: '#f59e0b',
  Query: '#ef4444',
  default: '#6b7280',
};

const LINK_COLORS = {
  RELATES_TO: '#6b7280',
  CONTAINS: '#3b82f6',
  CREATED_BY: '#f59e0b',
  MENTIONS: '#10b981',
  SIMILAR_TO: '#8b5cf6',
  default: '#d1d5db',
};

export const GraphVisualization: React.FC<GraphVisualizationProps> = ({
  data,
  width = 800,
  height = 600,
  onNodeSelect,
  onNodeDoubleClick,
  className = '',
}) => {
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [highlightedNodes, setHighlightedNodes] = useState<Set<string>>(
    new Set()
  );
  const [zoomLevel, setZoomLevel] = useState(1);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const { toast } = useToast();

  // D3 simulation refs
  const simulationRef = useRef<d3.Simulation<GraphNode, GraphLink> | null>(
    null
  );
  const transformRef = useRef(d3.zoomIdentity);

  const handleNodeClick = useCallback(
    (event: MouseEvent, node: GraphNode) => {
      event.stopPropagation();
      setSelectedNode(node);
      onNodeSelect?.(node);
    },
    [onNodeSelect]
  );

  const handleNodeDoubleClick = useCallback(
    (event: MouseEvent, node: GraphNode) => {
      event.stopPropagation();
      onNodeDoubleClick?.(node);
    },
    [onNodeDoubleClick]
  );

  const searchNodes = useCallback(
    (term: string) => {
      if (!term.trim()) {
        setHighlightedNodes(new Set());
        return;
      }

      const matches = new Set<string>();
      data.nodes.forEach(node => {
        if (
          node.label.toLowerCase().includes(term.toLowerCase()) ||
          node.type.toLowerCase().includes(term.toLowerCase()) ||
          Object.values(node.properties).some(prop =>
            String(prop).toLowerCase().includes(term.toLowerCase())
          )
        ) {
          matches.add(node.id);
        }
      });

      setHighlightedNodes(matches);

      if (matches.size === 0) {
        toast({
          title: 'No matches found',
          description: `No nodes match the search term "${term}"`,
          variant: 'default',
        });
      }
    },
    [data.nodes, toast]
  );

  const zoomIn = useCallback(() => {
    if (svgRef.current) {
      const svg = d3.select(svgRef.current);
      svg
        .transition()
        .duration(300)
        .call(d3.zoom<SVGSVGElement, unknown>().scaleBy as any, 1.5);
    }
  }, []);

  const zoomOut = useCallback(() => {
    if (svgRef.current) {
      const svg = d3.select(svgRef.current);
      svg
        .transition()
        .duration(300)
        .call(d3.zoom<SVGSVGElement, unknown>().scaleBy as any, 1 / 1.5);
    }
  }, []);

  const resetView = useCallback(() => {
    if (svgRef.current) {
      const svg = d3.select(svgRef.current);
      svg
        .transition()
        .duration(500)
        .call(
          d3.zoom<SVGSVGElement, unknown>().transform as any,
          d3.zoomIdentity
        );
      setZoomLevel(1);
    }
  }, []);

  const exportSVG = useCallback(() => {
    if (svgRef.current) {
      const svgData = new XMLSerializer().serializeToString(svgRef.current);
      const svgBlob = new Blob([svgData], {
        type: 'image/svg+xml;charset=utf-8',
      });
      const svgUrl = URL.createObjectURL(svgBlob);
      const downloadLink = document.createElement('a');
      downloadLink.href = svgUrl;
      downloadLink.download = `knowledge-graph-${new Date().toISOString().slice(0, 10)}.svg`;
      document.body.appendChild(downloadLink);
      downloadLink.click();
      document.body.removeChild(downloadLink);
      URL.revokeObjectURL(svgUrl);

      toast({
        title: 'Graph exported',
        description: 'SVG file downloaded successfully',
        variant: 'default',
      });
    }
  }, [toast]);

  useEffect(() => {
    if (!svgRef.current || !data.nodes.length) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    const container = svg.append('g').attr('class', 'graph-container');

    // Set up zoom behavior
    const zoom = d3
      .zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.1, 10])
      .on('zoom', event => {
        const { transform } = event;
        container.attr('transform', transform);
        transformRef.current = transform;
        setZoomLevel(Math.round(transform.k * 100) / 100);
      });

    svg.call(zoom);

    // Create force simulation
    const simulation = d3
      .forceSimulation<GraphNode>(data.nodes)
      .force(
        'link',
        d3
          .forceLink<GraphNode, GraphLink>(data.links)
          .id(d => d.id)
          .distance(100)
          .strength(0.5)
      )
      .force('charge', d3.forceManyBody().strength(-300))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collision', d3.forceCollide().radius(30));

    simulationRef.current = simulation;

    // Create links
    const link = container
      .append('g')
      .attr('class', 'links')
      .selectAll('line')
      .data(data.links)
      .enter()
      .append('line')
      .attr(
        'stroke',
        d =>
          LINK_COLORS[d.type as keyof typeof LINK_COLORS] || LINK_COLORS.default
      )
      .attr('stroke-opacity', 0.6)
      .attr('stroke-width', 2);

    // Create link labels
    const linkLabel = container
      .append('g')
      .attr('class', 'link-labels')
      .selectAll('text')
      .data(data.links)
      .enter()
      .append('text')
      .attr('font-size', '10px')
      .attr('font-family', 'Arial, sans-serif')
      .attr('fill', '#666')
      .attr('text-anchor', 'middle')
      .text(d => d.type);

    // Create nodes
    const node = container
      .append('g')
      .attr('class', 'nodes')
      .selectAll('g')
      .data(data.nodes)
      .enter()
      .append('g')
      .attr('class', 'node')
      .call(
        d3
          .drag<SVGGElement, GraphNode>()
          .on('start', (event, d) => {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
          })
          .on('drag', (event, d) => {
            d.fx = event.x;
            d.fy = event.y;
          })
          .on('end', (event, d) => {
            if (!event.active) simulation.alphaTarget(0);
            d.fx = null;
            d.fy = null;
          })
      );

    // Add circles to nodes
    node
      .append('circle')
      .attr('r', d => Math.max(15, Math.min(25, d.label.length * 2 + 10)))
      .attr(
        'fill',
        d =>
          NODE_COLORS[d.type as keyof typeof NODE_COLORS] || NODE_COLORS.default
      )
      .attr('stroke', '#fff')
      .attr('stroke-width', 2)
      .style('cursor', 'pointer');

    // Add labels to nodes
    node
      .append('text')
      .attr('dy', '.35em')
      .attr('text-anchor', 'middle')
      .attr('font-size', '12px')
      .attr('font-family', 'Arial, sans-serif')
      .attr('fill', '#fff')
      .attr('font-weight', 'bold')
      .style('pointer-events', 'none')
      .text(d =>
        d.label.length > 12 ? d.label.substring(0, 12) + '...' : d.label
      );

    // Add event listeners
    node
      .on('click', handleNodeClick)
      .on('dblclick', handleNodeDoubleClick)
      .on('mouseover', function (event, d) {
        d3.select(this)
          .select('circle')
          .transition()
          .duration(200)
          .attr('r', d => Math.max(20, Math.min(30, d.label.length * 2 + 15)));

        // Show tooltip
        const tooltip = d3
          .select('body')
          .append('div')
          .attr('class', 'graph-tooltip')
          .style('opacity', 0)
          .style('position', 'absolute')
          .style('background', 'rgba(0, 0, 0, 0.8)')
          .style('color', 'white')
          .style('padding', '8px')
          .style('border-radius', '4px')
          .style('font-size', '12px')
          .style('pointer-events', 'none')
          .style('z-index', '1000');

        tooltip.transition().duration(200).style('opacity', 0.9);

        tooltip
          .html(
            `
          <strong>${d.label}</strong><br/>
          Type: ${d.type}<br/>
          ID: ${d.id}
        `
          )
          .style('left', event.pageX + 10 + 'px')
          .style('top', event.pageY - 28 + 'px');
      })
      .on('mouseout', function (event, d) {
        d3.select(this)
          .select('circle')
          .transition()
          .duration(200)
          .attr('r', d => Math.max(15, Math.min(25, d.label.length * 2 + 10)));

        d3.selectAll('.graph-tooltip').remove();
      });

    // Update positions on tick
    simulation.on('tick', () => {
      link
        .attr('x1', d => (d.source as GraphNode).x!)
        .attr('y1', d => (d.source as GraphNode).y!)
        .attr('x2', d => (d.target as GraphNode).x!)
        .attr('y2', d => (d.target as GraphNode).y!);

      linkLabel
        .attr(
          'x',
          d => ((d.source as GraphNode).x! + (d.target as GraphNode).x!) / 2
        )
        .attr(
          'y',
          d => ((d.source as GraphNode).y! + (d.target as GraphNode).y!) / 2
        );

      node.attr('transform', d => `translate(${d.x},${d.y})`);
    });

    // Highlight searched nodes
    node
      .select('circle')
      .attr('stroke', d => (highlightedNodes.has(d.id) ? '#fbbf24' : '#fff'))
      .attr('stroke-width', d => (highlightedNodes.has(d.id) ? 4 : 2));

    return () => {
      simulation.stop();
    };
  }, [
    data,
    width,
    height,
    highlightedNodes,
    handleNodeClick,
    handleNodeDoubleClick,
  ]);

  const toggleFullscreen = () => {
    if (!isFullscreen) {
      containerRef.current?.requestFullscreen?.();
    } else {
      document.exitFullscreen?.();
    }
    setIsFullscreen(!isFullscreen);
  };

  return (
    <Card
      className={`${className} ${isFullscreen ? 'fixed inset-0 z-50' : ''}`}
    >
      <CardHeader className='pb-2'>
        <div className='flex items-center justify-between'>
          <CardTitle className='flex items-center gap-2'>
            Knowledge Graph
            <Badge variant='secondary'>
              {data.nodes.length} nodes, {data.links.length} links
            </Badge>
          </CardTitle>
          <div className='flex items-center gap-2'>
            <div className='flex items-center gap-1 mr-4'>
              <Search className='w-4 h-4 text-gray-500' />
              <Input
                placeholder='Search nodes...'
                value={searchTerm}
                onChange={e => setSearchTerm(e.target.value)}
                onKeyPress={e => e.key === 'Enter' && searchNodes(searchTerm)}
                className='w-48'
              />
              <Button
                variant='outline'
                size='sm'
                onClick={() => searchNodes(searchTerm)}
              >
                Go
              </Button>
            </div>
            <Badge variant='outline'>Zoom: {zoomLevel}x</Badge>
            <Button variant='outline' size='sm' onClick={zoomIn}>
              <ZoomIn className='w-4 h-4' />
            </Button>
            <Button variant='outline' size='sm' onClick={zoomOut}>
              <ZoomOut className='w-4 h-4' />
            </Button>
            <Button variant='outline' size='sm' onClick={resetView}>
              <RotateCcw className='w-4 h-4' />
            </Button>
            <Button variant='outline' size='sm' onClick={exportSVG}>
              <Download className='w-4 h-4' />
            </Button>
            <Button variant='outline' size='sm' onClick={toggleFullscreen}>
              <Maximize className='w-4 h-4' />
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className='p-0'>
        <div ref={containerRef} className='relative'>
          <svg
            ref={svgRef}
            width={width}
            height={height}
            className='border border-gray-200 bg-white'
            style={{ cursor: 'grab' }}
          />

          {selectedNode && (
            <div className='absolute top-4 right-4 bg-white p-4 rounded-lg shadow-lg border max-w-sm'>
              <h3 className='font-semibold text-lg mb-2'>
                {selectedNode.label}
              </h3>
              <div className='space-y-2 text-sm'>
                <div>
                  <span className='font-medium'>Type:</span>
                  <Badge
                    className='ml-2'
                    style={{
                      backgroundColor:
                        NODE_COLORS[
                          selectedNode.type as keyof typeof NODE_COLORS
                        ],
                    }}
                  >
                    {selectedNode.type}
                  </Badge>
                </div>
                <div>
                  <span className='font-medium'>ID:</span>
                  <code className='ml-2 text-xs bg-gray-100 px-1 py-0.5 rounded'>
                    {selectedNode.id}
                  </code>
                </div>
                {Object.entries(selectedNode.properties).length > 0 && (
                  <div>
                    <span className='font-medium'>Properties:</span>
                    <div className='mt-1 space-y-1'>
                      {Object.entries(selectedNode.properties)
                        .slice(0, 5)
                        .map(([key, value]) => (
                          <div key={key} className='text-xs'>
                            <span className='text-gray-600'>{key}:</span>
                            <span className='ml-1'>
                              {String(value).substring(0, 50)}
                              {String(value).length > 50 ? '...' : ''}
                            </span>
                          </div>
                        ))}
                    </div>
                  </div>
                )}
                <Button
                  variant='outline'
                  size='sm'
                  onClick={() => setSelectedNode(null)}
                  className='mt-2 w-full'
                >
                  Close
                </Button>
              </div>
            </div>
          )}

          {/* Legend */}
          <div className='absolute bottom-4 left-4 bg-white p-3 rounded-lg shadow border'>
            <h4 className='font-semibold text-sm mb-2'>Node Types</h4>
            <div className='space-y-1 text-xs'>
              {Object.entries(NODE_COLORS)
                .filter(([type]) => type !== 'default')
                .map(([type, color]) => (
                  <div key={type} className='flex items-center gap-2'>
                    <div
                      className='w-3 h-3 rounded-full'
                      style={{ backgroundColor: color }}
                    ></div>
                    <span>{type}</span>
                  </div>
                ))}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

export default GraphVisualization;
