import React, { useState, useEffect, useCallback } from 'react';
import { NextPage } from 'next';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { GraphVisualization } from '@/components/knowledge-graph/GraphVisualization';
import { GraphQueryInterface } from '@/components/knowledge-graph/GraphQueryInterface';
import {
  Brain,
  Network,
  Search,
  TrendingUp,
  Database,
  Activity,
  Zap,
  Target,
  RefreshCw,
  AlertTriangle,
} from 'lucide-react';
import { useToast } from '@/hooks/use-toast';

interface GraphData {
  nodes: Array<{
    id: string;
    label: string;
    type: string;
    properties: Record<string, unknown>;
  }>;
  links: Array<{
    source: string;
    target: string;
    type: string;
    properties: Record<string, unknown>;
  }>;
}

interface GraphStats {
  totalNodes: number;
  totalRelationships: number;
  nodeTypes: Record<string, number>;
  relationshipTypes: Record<string, number>;
  lastUpdated: string;
}

interface GraphInsight {
  id: string;
  type: 'cluster' | 'anomaly' | 'pattern' | 'recommendation';
  title: string;
  description: string;
  confidence: number;
  data: unknown;
  created_at: string;
}

const KnowledgeGraphPage: NextPage = () => {
  const [graphData, setGraphData] = useState<GraphData>({
    nodes: [],
    links: [],
  });
  const [graphStats, setGraphStats] = useState<GraphStats | null>(null);
  const [insights, setInsights] = useState<GraphInsight[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedNode, setSelectedNode] = useState<any>(null);
  const [activeTab, setActiveTab] = useState('visualization');
  const [isConnected, setIsConnected] = useState(false);
  const [connectionError, setConnectionError] = useState<string | null>(null);

  const { toast } = useToast();

  // API base URL
  const API_BASE =
    process.env.NEXT_PUBLIC_KNOWLEDGE_GRAPH_API ||
    'http://localhost:3005/api/graph';

  // Load initial graph data
  const loadGraphData = useCallback(async () => {
    setIsLoading(true);
    try {
      // Load overview data
      const overviewResponse = await fetch(`${API_BASE}/overview`);
      if (!overviewResponse.ok)
        throw new Error('Failed to fetch graph overview');
      const overviewData = await overviewResponse.json();

      if (overviewData.success) {
        setGraphStats(overviewData.data.statistics);
        setIsConnected(true);
        setConnectionError(null);
      }

      // Load sample graph data for visualization
      const queryResponse = await fetch(`${API_BASE}/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: 'MATCH (n)-[r]-(m) RETURN n, r, m LIMIT 50',
        }),
      });

      if (queryResponse.ok) {
        const queryResult = await queryResponse.json();
        if (queryResult.success) {
          // Transform Neo4j result to D3-compatible format
          const nodes = new Map();
          const links = [];

          queryResult.data.forEach((record: unknown) => {
            // Extract nodes
            ['n', 'm'].forEach(key => {
              if (record[key]) {
                const node = record[key];
                if (!nodes.has(node.identity)) {
                  nodes.set(node.identity, {
                    id: node.identity,
                    label:
                      node.properties.name ||
                      node.properties.title ||
                      node.labels?.[0] ||
                      'Node',
                    type: node.labels?.[0] || 'Unknown',
                    properties: node.properties,
                  });
                }
              }
            });

            // Extract relationships
            if (record.r) {
              const rel = record.r;
              links.push({
                source: rel.start,
                target: rel.end,
                type: rel.type,
                properties: rel.properties,
              });
            }
          });

          setGraphData({
            nodes: Array.from(nodes.values()),
            links,
          });
        }
      }

      // Load insights
      const insightsResponse = await fetch(`${API_BASE}/insights`);
      if (insightsResponse.ok) {
        const insightsResult = await insightsResponse.json();
        if (insightsResult.success) {
          setInsights(insightsResult.data.insights);
        }
      }
    } catch (error) {
      console.error('Failed to load graph data:', error);
      setConnectionError(
        error instanceof Error ? error.message : 'Connection failed'
      );
      setIsConnected(false);
      toast({
        title: 'Connection Error',
        description: 'Failed to connect to Knowledge Graph service',
        variant: 'destructive',
      });
    } finally {
      setIsLoading(false);
    }
  }, [API_BASE, toast]);

  // Execute Cypher queries
  const executeQuery = useCallback(
    async (query: string) => {
      const response = await fetch(`${API_BASE}/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query }),
      });

      if (!response.ok) {
        throw new Error(`Query failed: ${response.statusText}`);
      }

      const result = await response.json();
      if (!result.success) {
        throw new Error(result.error || 'Query execution failed');
      }

      return {
        data: result.data,
        execution_time: result.execution_time || 0,
        records_returned: result.data.length,
        query,
        timestamp: new Date().toISOString(),
      };
    },
    [API_BASE]
  );

  // Handle node selection
  const handleNodeSelect = useCallback((node: unknown) => {
    setSelectedNode(node);
  }, []);

  // Handle node double click
  const handleNodeDoubleClick = useCallback(
    async (node: unknown) => {
      try {
        const response = await fetch(
          `${API_BASE}/nodes/${node.id}?relationships=true`
        );
        if (response.ok) {
          const result = await response.json();
          if (result.success) {
            toast({
              title: 'Node Details',
              description: `${node.label} has ${result.data.relationships.length} relationships`,
              variant: 'default',
            });
          }
        }
      } catch (error) {
        console.error('Failed to fetch node details:', error);
      }
    },
    [API_BASE, toast]
  );

  // Setup real-time updates
  useEffect(() => {
    if (!isConnected) return;

    const eventSource = new EventSource(`${API_BASE}/stream`);

    eventSource.onmessage = event => {
      try {
        const data = JSON.parse(event.data);

        switch (data.type) {
          case 'graph_update':
            // Refresh graph data on updates
            loadGraphData();
            break;
          case 'insight':
            // Add new insight
            setInsights(prev => [data.data, ...prev.slice(0, 9)]); // Keep latest 10
            toast({
              title: 'New Insight',
              description: data.data.title,
              variant: 'default',
            });
            break;
        }
      } catch (error) {
        console.error('Failed to parse SSE data:', error);
      }
    };

    eventSource.onerror = () => {
      setConnectionError('Real-time connection lost');
    };

    return () => {
      eventSource.close();
    };
  }, [isConnected, API_BASE, loadGraphData, toast]);

  // Load data on mount
  useEffect(() => {
    loadGraphData();
  }, [loadGraphData]);

  const getInsightIcon = (type: string) => {
    switch (type) {
      case 'cluster':
        return <Network className='w-4 h-4' />;
      case 'anomaly':
        return <AlertTriangle className='w-4 h-4' />;
      case 'pattern':
        return <TrendingUp className='w-4 h-4' />;
      case 'recommendation':
        return <Target className='w-4 h-4' />;
      default:
        return <Zap className='w-4 h-4' />;
    }
  };

  const getInsightColor = (type: string) => {
    switch (type) {
      case 'cluster':
        return 'bg-blue-100 text-blue-800';
      case 'anomaly':
        return 'bg-red-100 text-red-800';
      case 'pattern':
        return 'bg-green-100 text-green-800';
      case 'recommendation':
        return 'bg-purple-100 text-purple-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  if (!isConnected && !isLoading) {
    return (
      <div className='container mx-auto px-4 py-8'>
        <Card>
          <CardContent className='flex flex-col items-center justify-center py-16'>
            <AlertTriangle className='w-16 h-16 text-red-500 mb-4' />
            <h2 className='text-2xl font-bold mb-2'>
              Knowledge Graph Unavailable
            </h2>
            <p className='text-gray-600 mb-4 text-center max-w-md'>
              {connectionError ||
                'Unable to connect to the Knowledge Graph service. Please ensure Neo4j is running and the service is started.'}
            </p>
            <Button onClick={loadGraphData} className='flex items-center gap-2'>
              <RefreshCw className='w-4 h-4' />
              Retry Connection
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className='container mx-auto px-4 py-8'>
      {/* Header */}
      <div className='mb-8'>
        <div className='flex items-center justify-between'>
          <div className='flex items-center gap-3'>
            <Brain className='w-8 h-8 text-purple-600' />
            <div>
              <h1 className='text-3xl font-bold'>Knowledge Graph</h1>
              <p className='text-gray-600'>
                Explore and query your intelligent knowledge network
              </p>
            </div>
          </div>
          <div className='flex items-center gap-2'>
            <Badge variant={isConnected ? 'default' : 'destructive'}>
              <Activity className='w-3 h-3 mr-1' />
              {isConnected ? 'Connected' : 'Disconnected'}
            </Badge>
            <Button
              onClick={loadGraphData}
              disabled={isLoading}
              variant='outline'
            >
              <RefreshCw
                className={`w-4 h-4 mr-2 ${isLoading ? 'animate-spin' : ''}`}
              />
              Refresh
            </Button>
          </div>
        </div>
      </div>

      {/* Statistics Overview */}
      {graphStats && (
        <div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8'>
          <Card>
            <CardContent className='flex items-center p-6'>
              <Database className='w-8 h-8 text-blue-600 mr-3' />
              <div>
                <p className='text-sm font-medium text-gray-600'>Total Nodes</p>
                <p className='text-2xl font-bold'>
                  {graphStats.totalNodes.toLocaleString()}
                </p>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className='flex items-center p-6'>
              <Network className='w-8 h-8 text-green-600 mr-3' />
              <div>
                <p className='text-sm font-medium text-gray-600'>
                  Relationships
                </p>
                <p className='text-2xl font-bold'>
                  {graphStats.totalRelationships.toLocaleString()}
                </p>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className='flex items-center p-6'>
              <TrendingUp className='w-8 h-8 text-purple-600 mr-3' />
              <div>
                <p className='text-sm font-medium text-gray-600'>Node Types</p>
                <p className='text-2xl font-bold'>
                  {Object.keys(graphStats.nodeTypes).length}
                </p>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className='flex items-center p-6'>
              <Zap className='w-8 h-8 text-orange-600 mr-3' />
              <div>
                <p className='text-sm font-medium text-gray-600'>Insights</p>
                <p className='text-2xl font-bold'>{insights.length}</p>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Main Interface */}
      <div className='grid grid-cols-1 xl:grid-cols-4 gap-6'>
        {/* Main Content Area */}
        <div className='xl:col-span-3'>
          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList className='grid w-full grid-cols-2'>
              <TabsTrigger value='visualization'>
                Graph Visualization
              </TabsTrigger>
              <TabsTrigger value='query'>Query Interface</TabsTrigger>
            </TabsList>

            <TabsContent value='visualization' className='mt-4'>
              <GraphVisualization
                data={graphData}
                width={800}
                height={600}
                onNodeSelect={handleNodeSelect}
                onNodeDoubleClick={handleNodeDoubleClick}
                className='w-full'
              />
            </TabsContent>

            <TabsContent value='query' className='mt-4'>
              <GraphQueryInterface
                onQueryExecute={executeQuery}
                onQueryResult={result => {
                  // Handle query result visualization updates if needed
                  console.log('Query result:', result);
                }}
              />
            </TabsContent>
          </Tabs>
        </div>

        {/* Sidebar */}
        <div className='space-y-6'>
          {/* Selected Node Details */}
          {selectedNode && (
            <Card>
              <CardHeader>
                <CardTitle className='flex items-center gap-2'>
                  <Search className='w-4 h-4' />
                  Selected Node
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className='space-y-3'>
                  <div>
                    <h3 className='font-semibold text-lg'>
                      {selectedNode.label}
                    </h3>
                    <Badge className='mt-1'>{selectedNode.type}</Badge>
                  </div>

                  <div className='text-sm'>
                    <p className='font-medium text-gray-600'>ID:</p>
                    <code className='text-xs bg-gray-100 px-2 py-1 rounded'>
                      {selectedNode.id}
                    </code>
                  </div>

                  {Object.keys(selectedNode.properties).length > 0 && (
                    <div className='text-sm'>
                      <p className='font-medium text-gray-600 mb-2'>
                        Properties:
                      </p>
                      <div className='space-y-1'>
                        {Object.entries(selectedNode.properties)
                          .slice(0, 5)
                          .map(([key, value]) => (
                            <div key={key} className='flex justify-between'>
                              <span className='text-gray-600'>{key}:</span>
                              <span className='font-mono text-xs'>
                                {String(value).length > 20
                                  ? String(value).substring(0, 20) + '...'
                                  : String(value)}
                              </span>
                            </div>
                          ))}
                      </div>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Recent Insights */}
          <Card>
            <CardHeader>
              <CardTitle className='flex items-center gap-2'>
                <Brain className='w-4 h-4' />
                Recent Insights
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className='space-y-3'>
                {insights.length > 0 ? (
                  insights.slice(0, 5).map(insight => (
                    <div key={insight.id} className='border rounded-lg p-3'>
                      <div className='flex items-start gap-2 mb-2'>
                        <Badge
                          className={`text-xs ${getInsightColor(insight.type)}`}
                        >
                          {getInsightIcon(insight.type)}
                          <span className='ml-1 capitalize'>
                            {insight.type}
                          </span>
                        </Badge>
                        <Badge variant='outline' className='text-xs'>
                          {Math.round(insight.confidence * 100)}%
                        </Badge>
                      </div>

                      <h4 className='font-medium text-sm mb-1'>
                        {insight.title}
                      </h4>
                      <p className='text-xs text-gray-600 mb-2'>
                        {insight.description}
                      </p>

                      <div className='text-xs text-gray-400'>
                        {new Date(insight.created_at).toLocaleString()}
                      </div>
                    </div>
                  ))
                ) : (
                  <div className='text-center py-8 text-gray-500'>
                    <Brain className='w-8 h-8 mx-auto mb-2 opacity-50' />
                    <p className='text-sm'>No insights available yet</p>
                    <p className='text-xs'>
                      Insights will appear as the graph learns
                    </p>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Node Type Distribution */}
          {graphStats && (
            <Card>
              <CardHeader>
                <CardTitle className='flex items-center gap-2'>
                  <Database className='w-4 h-4' />
                  Node Distribution
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className='space-y-2'>
                  {Object.entries(graphStats.nodeTypes)
                    .sort(([, a], [, b]) => b - a)
                    .slice(0, 10)
                    .map(([type, count]) => (
                      <div
                        key={type}
                        className='flex items-center justify-between text-sm'
                      >
                        <span className='text-gray-600'>{type}</span>
                        <Badge variant='secondary'>
                          {count.toLocaleString()}
                        </Badge>
                      </div>
                    ))}
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
};

export default KnowledgeGraphPage;
