import React, { useState, useCallback, useRef, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  Play,
  Save,
  History,
  BookOpen,
  Download,
  Copy,
  Check,
  AlertCircle,
  Clock,
  Database,
} from 'lucide-react';
import { useToast } from '@/hooks/use-toast';

interface QueryResult {
  data: unknown[];
  execution_time: number;
  records_returned: number;
  query: string;
  timestamp: string;
}

interface SavedQuery {
  id: string;
  name: string;
  query: string;
  description?: string;
  created_at: string;
  last_used?: string;
  usage_count: number;
}

interface GraphQueryInterfaceProps {
  onQueryExecute: (query: string) => Promise<QueryResult>;
  onQueryResult?: (result: QueryResult) => void;
  className?: string;
}

const QUERY_EXAMPLES = {
  basic: [
    {
      name: 'All Nodes',
      query: 'MATCH (n) RETURN n LIMIT 25',
      description: 'Get all nodes in the graph (limited to 25)',
    },
    {
      name: 'All Relationships',
      query: 'MATCH (a)-[r]->(b) RETURN a, r, b LIMIT 25',
      description: 'Get all relationships between nodes',
    },
    {
      name: 'Node Count by Type',
      query:
        'MATCH (n) RETURN labels(n) as type, count(n) as count ORDER BY count DESC',
      description: 'Count nodes grouped by type',
    },
  ],
  entities: [
    {
      name: 'Find Entities by Type',
      query: 'MATCH (e:Entity) WHERE e.type = "PERSON" RETURN e LIMIT 20',
      description: 'Find all person entities',
    },
    {
      name: 'Highly Connected Entities',
      query:
        'MATCH (e:Entity)-[r]-(n) RETURN e, count(r) as connections ORDER BY connections DESC LIMIT 10',
      description: 'Find entities with most connections',
    },
    {
      name: 'Entity Co-occurrences',
      query:
        'MATCH (e1:Entity)-[:MENTIONED_IN]->(d:Document)<-[:MENTIONED_IN]-(e2:Entity) WHERE e1 <> e2 RETURN e1, e2, count(d) as shared_docs ORDER BY shared_docs DESC LIMIT 15',
      description: 'Find entities that appear together in documents',
    },
  ],
  documents: [
    {
      name: 'Recent Documents',
      query: 'MATCH (d:Document) RETURN d ORDER BY d.createdAt DESC LIMIT 10',
      description: 'Get most recently created documents',
    },
    {
      name: 'Documents by Content Type',
      query:
        'MATCH (d:Document) RETURN d.contentType, count(d) as count ORDER BY count DESC',
      description: 'Group documents by content type',
    },
    {
      name: 'Document Entity Networks',
      query:
        'MATCH (d:Document)-[:CONTAINS]->(e:Entity)-[r]-(other) RETURN d, e, r, other LIMIT 30',
      description: 'Show entity networks within documents',
    },
  ],
  paths: [
    {
      name: 'Shortest Path',
      query:
        'MATCH (start), (end), path = shortestPath((start)-[*..5]-(end)) WHERE start.id = "node1" AND end.id = "node2" RETURN path',
      description: 'Find shortest path between two nodes',
    },
    {
      name: 'Knowledge Paths',
      query:
        'MATCH path = (concept:Concept)-[:RELATES_TO*2..4]-(related:Concept) WHERE concept.name CONTAINS "machine learning" RETURN path LIMIT 10',
      description: 'Find knowledge paths from a concept',
    },
  ],
  analytics: [
    {
      name: 'Graph Statistics',
      query:
        'CALL apoc.meta.stats() YIELD labels, relTypesCount RETURN labels, relTypesCount',
      description: 'Get comprehensive graph statistics',
    },
    {
      name: 'Centrality Analysis',
      query:
        'MATCH (n)-[r]-() RETURN n.id, n.name, count(r) as degree ORDER BY degree DESC LIMIT 20',
      description: 'Find most central nodes by degree',
    },
  ],
};

export const GraphQueryInterface: React.FC<GraphQueryInterfaceProps> = ({
  onQueryExecute,
  onQueryResult,
  className = '',
}) => {
  const [query, setQuery] = useState('');
  const [isExecuting, setIsExecuting] = useState(false);
  const [queryResult, setQueryResult] = useState<QueryResult | null>(null);
  const [queryError, setQueryError] = useState<string | null>(null);
  const [queryHistory, setQueryHistory] = useState<QueryResult[]>([]);
  const [savedQueries, setSavedQueries] = useState<SavedQuery[]>([]);
  const [saveQueryName, setSaveQueryName] = useState('');
  const [saveQueryDescription, setSaveQueryDescription] = useState('');
  const [showSaveDialog, setShowSaveDialog] = useState(false);
  const [copiedQuery, setCopiedQuery] = useState('');

  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const { toast } = useToast();

  // Load saved queries and history from localStorage
  useEffect(() => {
    const saved = localStorage.getItem('graph-saved-queries');
    if (saved) {
      setSavedQueries(JSON.parse(saved));
    }

    const history = localStorage.getItem('graph-query-history');
    if (history) {
      setQueryHistory(JSON.parse(history));
    }
  }, []);

  const executeQuery = useCallback(async () => {
    if (!query.trim()) {
      toast({
        title: 'Empty query',
        description: 'Please enter a Cypher query to execute',
        variant: 'destructive',
      });
      return;
    }

    setIsExecuting(true);
    setQueryError(null);

    try {
      const result = await onQueryExecute(query);
      setQueryResult(result);
      onQueryResult?.(result);

      // Add to history
      const newHistory = [result, ...queryHistory.slice(0, 9)]; // Keep last 10
      setQueryHistory(newHistory);
      localStorage.setItem('graph-query-history', JSON.stringify(newHistory));

      toast({
        title: 'Query executed successfully',
        description: `Returned ${result.records_returned} records in ${result.execution_time}ms`,
        variant: 'default',
      });
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : 'Query execution failed';
      setQueryError(errorMessage);
      toast({
        title: 'Query execution failed',
        description: errorMessage,
        variant: 'destructive',
      });
    } finally {
      setIsExecuting(false);
    }
  }, [query, queryHistory, onQueryExecute, onQueryResult, toast]);

  const loadExampleQuery = useCallback((exampleQuery: string) => {
    setQuery(exampleQuery);
    textareaRef.current?.focus();
  }, []);

  const copyQuery = useCallback(
    async (queryText: string) => {
      try {
        await navigator.clipboard.writeText(queryText);
        setCopiedQuery(queryText);
        setTimeout(() => setCopiedQuery(''), 2000);
        toast({
          title: 'Copied to clipboard',
          description: 'Query copied successfully',
          variant: 'default',
        });
      } catch (error) {
        toast({
          title: 'Copy failed',
          description: 'Failed to copy query to clipboard',
          variant: 'destructive',
        });
      }
    },
    [toast]
  );

  const saveQuery = useCallback(() => {
    if (!query.trim() || !saveQueryName.trim()) {
      toast({
        title: 'Missing information',
        description: 'Please provide both query and name',
        variant: 'destructive',
      });
      return;
    }

    const newQuery: SavedQuery = {
      id: Date.now().toString(),
      name: saveQueryName,
      query: query.trim(),
      description: saveQueryDescription.trim() || undefined,
      created_at: new Date().toISOString(),
      usage_count: 0,
    };

    const updated = [newQuery, ...savedQueries];
    setSavedQueries(updated);
    localStorage.setItem('graph-saved-queries', JSON.stringify(updated));

    setSaveQueryName('');
    setSaveQueryDescription('');
    setShowSaveDialog(false);

    toast({
      title: 'Query saved',
      description: `Query "${saveQueryName}" saved successfully`,
      variant: 'default',
    });
  }, [query, saveQueryName, saveQueryDescription, savedQueries, toast]);

  const loadSavedQuery = useCallback(
    (savedQuery: SavedQuery) => {
      setQuery(savedQuery.query);

      // Update usage statistics
      const updated = savedQueries.map(q =>
        q.id === savedQuery.id
          ? {
              ...q,
              usage_count: q.usage_count + 1,
              last_used: new Date().toISOString(),
            }
          : q
      );
      setSavedQueries(updated);
      localStorage.setItem('graph-saved-queries', JSON.stringify(updated));

      textareaRef.current?.focus();
    },
    [savedQueries]
  );

  const deleteSavedQuery = useCallback(
    (queryId: string) => {
      const updated = savedQueries.filter(q => q.id !== queryId);
      setSavedQueries(updated);
      localStorage.setItem('graph-saved-queries', JSON.stringify(updated));

      toast({
        title: 'Query deleted',
        description: 'Saved query removed successfully',
        variant: 'default',
      });
    },
    [savedQueries, toast]
  );

  const formatJsonResult = (data: unknown) => {
    try {
      return JSON.stringify(data, null, 2);
    } catch {
      return String(data);
    }
  };

  const downloadResults = useCallback(() => {
    if (!queryResult) return;

    const dataStr = JSON.stringify(queryResult, null, 2);
    const dataUri =
      'data:application/json;charset=utf-8,' + encodeURIComponent(dataStr);

    const exportFileDefaultName = `graph-query-results-${new Date().toISOString().slice(0, 19)}.json`;

    const linkElement = document.createElement('a');
    linkElement.setAttribute('href', dataUri);
    linkElement.setAttribute('download', exportFileDefaultName);
    linkElement.click();

    toast({
      title: 'Results downloaded',
      description: 'Query results exported to JSON file',
      variant: 'default',
    });
  }, [queryResult, toast]);

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Query Input */}
      <Card>
        <CardHeader>
          <CardTitle className='flex items-center gap-2'>
            <Database className='w-5 h-5' />
            Cypher Query Interface
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className='space-y-4'>
            <div className='relative'>
              <Textarea
                ref={textareaRef}
                placeholder='Enter your Cypher query here...'
                value={query}
                onChange={e => setQuery(e.target.value)}
                className='min-h-[120px] font-mono text-sm'
                onKeyDown={e => {
                  if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
                    e.preventDefault();
                    executeQuery();
                  }
                }}
              />
              {query && (
                <Button
                  variant='outline'
                  size='sm'
                  className='absolute top-2 right-2'
                  onClick={() => copyQuery(query)}
                >
                  {copiedQuery === query ? (
                    <Check className='w-4 h-4' />
                  ) : (
                    <Copy className='w-4 h-4' />
                  )}
                </Button>
              )}
            </div>

            <div className='flex items-center gap-2'>
              <Button
                onClick={executeQuery}
                disabled={isExecuting || !query.trim()}
                className='flex items-center gap-2'
              >
                <Play className='w-4 h-4' />
                {isExecuting ? 'Executing...' : 'Execute Query'}
              </Button>

              <Button
                variant='outline'
                onClick={() => setShowSaveDialog(true)}
                disabled={!query.trim()}
                className='flex items-center gap-2'
              >
                <Save className='w-4 h-4' />
                Save Query
              </Button>

              {queryResult && (
                <Button
                  variant='outline'
                  onClick={downloadResults}
                  className='flex items-center gap-2'
                >
                  <Download className='w-4 h-4' />
                  Download Results
                </Button>
              )}

              <div className='ml-auto text-sm text-gray-500'>
                Press Ctrl+Enter to execute
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Save Query Dialog */}
      {showSaveDialog && (
        <Card>
          <CardHeader>
            <CardTitle>Save Query</CardTitle>
          </CardHeader>
          <CardContent>
            <div className='space-y-4'>
              <Input
                placeholder='Query name'
                value={saveQueryName}
                onChange={e => setSaveQueryName(e.target.value)}
              />
              <Input
                placeholder='Description (optional)'
                value={saveQueryDescription}
                onChange={e => setSaveQueryDescription(e.target.value)}
              />
              <div className='flex gap-2'>
                <Button onClick={saveQuery}>Save</Button>
                <Button
                  variant='outline'
                  onClick={() => setShowSaveDialog(false)}
                >
                  Cancel
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Query Result */}
      {(queryResult || queryError) && (
        <Card>
          <CardHeader>
            <CardTitle className='flex items-center gap-2'>
              {queryError ? (
                <>
                  <AlertCircle className='w-5 h-5 text-red-500' />
                  Query Error
                </>
              ) : (
                <>
                  <Check className='w-5 h-5 text-green-500' />
                  Query Results
                </>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {queryError ? (
              <div className='text-red-600 font-mono text-sm bg-red-50 p-3 rounded border'>
                {queryError}
              </div>
            ) : queryResult ? (
              <div className='space-y-4'>
                <div className='flex items-center gap-4 text-sm text-gray-600'>
                  <Badge variant='outline'>
                    {queryResult.records_returned} records
                  </Badge>
                  <Badge variant='outline'>
                    <Clock className='w-3 h-3 mr-1' />
                    {queryResult.execution_time}ms
                  </Badge>
                  <span className='text-xs'>
                    Executed: {new Date(queryResult.timestamp).toLocaleString()}
                  </span>
                </div>

                <ScrollArea className='h-64 w-full border rounded'>
                  <pre className='p-4 text-xs font-mono'>
                    {formatJsonResult(queryResult.data)}
                  </pre>
                </ScrollArea>
              </div>
            ) : null}
          </CardContent>
        </Card>
      )}

      {/* Query Examples and History */}
      <Tabs defaultValue='examples' className='w-full'>
        <TabsList className='grid w-full grid-cols-3'>
          <TabsTrigger value='examples'>Query Examples</TabsTrigger>
          <TabsTrigger value='saved'>Saved Queries</TabsTrigger>
          <TabsTrigger value='history'>Query History</TabsTrigger>
        </TabsList>

        <TabsContent value='examples' className='space-y-4'>
          {Object.entries(QUERY_EXAMPLES).map(([category, queries]) => (
            <Card key={category}>
              <CardHeader>
                <CardTitle className='text-sm capitalize'>
                  {category} Queries
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className='space-y-2'>
                  {queries.map((example, index) => (
                    <div key={index} className='border rounded p-3'>
                      <div className='flex items-center justify-between mb-2'>
                        <h4 className='font-medium text-sm'>{example.name}</h4>
                        <div className='flex gap-1'>
                          <Button
                            variant='outline'
                            size='sm'
                            onClick={() => copyQuery(example.query)}
                          >
                            {copiedQuery === example.query ? (
                              <Check className='w-3 h-3' />
                            ) : (
                              <Copy className='w-3 h-3' />
                            )}
                          </Button>
                          <Button
                            variant='outline'
                            size='sm'
                            onClick={() => loadExampleQuery(example.query)}
                          >
                            Load
                          </Button>
                        </div>
                      </div>
                      <p className='text-xs text-gray-600 mb-2'>
                        {example.description}
                      </p>
                      <code className='text-xs bg-gray-100 p-2 rounded block'>
                        {example.query}
                      </code>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          ))}
        </TabsContent>

        <TabsContent value='saved' className='space-y-4'>
          {savedQueries.length > 0 ? (
            <div className='space-y-2'>
              {savedQueries.map(savedQuery => (
                <Card key={savedQuery.id}>
                  <CardContent className='pt-4'>
                    <div className='flex items-start justify-between'>
                      <div className='flex-1'>
                        <h4 className='font-medium text-sm mb-1'>
                          {savedQuery.name}
                        </h4>
                        {savedQuery.description && (
                          <p className='text-xs text-gray-600 mb-2'>
                            {savedQuery.description}
                          </p>
                        )}
                        <code className='text-xs bg-gray-100 p-2 rounded block mb-2'>
                          {savedQuery.query.substring(0, 100)}...
                        </code>
                        <div className='flex gap-2 text-xs text-gray-500'>
                          <span>Used: {savedQuery.usage_count} times</span>
                          <span>
                            Created:{' '}
                            {new Date(
                              savedQuery.created_at
                            ).toLocaleDateString()}
                          </span>
                        </div>
                      </div>
                      <div className='flex gap-1 ml-4'>
                        <Button
                          variant='outline'
                          size='sm'
                          onClick={() => copyQuery(savedQuery.query)}
                        >
                          <Copy className='w-3 h-3' />
                        </Button>
                        <Button
                          variant='outline'
                          size='sm'
                          onClick={() => loadSavedQuery(savedQuery)}
                        >
                          Load
                        </Button>
                        <Button
                          variant='outline'
                          size='sm'
                          onClick={() => deleteSavedQuery(savedQuery.id)}
                        >
                          Delete
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : (
            <Card>
              <CardContent className='pt-4'>
                <div className='text-center text-gray-500'>
                  <BookOpen className='w-8 h-8 mx-auto mb-2' />
                  <p>No saved queries yet</p>
                  <p className='text-sm'>
                    Execute queries and save them for future use
                  </p>
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value='history' className='space-y-4'>
          {queryHistory.length > 0 ? (
            <div className='space-y-2'>
              {queryHistory.map((result, index) => (
                <Card key={index}>
                  <CardContent className='pt-4'>
                    <div className='flex items-start justify-between'>
                      <div className='flex-1'>
                        <code className='text-xs bg-gray-100 p-2 rounded block mb-2'>
                          {result.query.substring(0, 100)}...
                        </code>
                        <div className='flex gap-4 text-xs text-gray-500'>
                          <span>{result.records_returned} records</span>
                          <span>{result.execution_time}ms</span>
                          <span>
                            {new Date(result.timestamp).toLocaleString()}
                          </span>
                        </div>
                      </div>
                      <div className='flex gap-1 ml-4'>
                        <Button
                          variant='outline'
                          size='sm'
                          onClick={() => copyQuery(result.query)}
                        >
                          <Copy className='w-3 h-3' />
                        </Button>
                        <Button
                          variant='outline'
                          size='sm'
                          onClick={() => loadExampleQuery(result.query)}
                        >
                          Load
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : (
            <Card>
              <CardContent className='pt-4'>
                <div className='text-center text-gray-500'>
                  <History className='w-8 h-8 mx-auto mb-2' />
                  <p>No query history yet</p>
                  <p className='text-sm'>Execute queries to see them here</p>
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default GraphQueryInterface;
