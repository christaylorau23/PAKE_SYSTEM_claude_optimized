/* Interactive Research Dashboard - Real-time Multi-Source Research Interface */
'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

interface SearchResult {
  id: string;
  title: string;
  content: string;
  source: 'web' | 'arxiv' | 'pubmed';
  url?: string;
  authors?: string[];
  publishedDate?: string;
  confidence?: number;
  metadata?: Record<string, unknown>;
}

interface ResearchQuery {
  query: string;
  sources: string[];
  status: 'idle' | 'searching' | 'completed' | 'error';
  results: SearchResult[];
  metrics: {
    totalResults: number;
    processingTime: number;
    sourcesQueried: number;
  };
}

const sourceIcons = {
  web: '🌐',
  arxiv: '📚',
  pubmed: '🔬',
};

const sourceColors = {
  web: 'border-blue-200 bg-blue-50 dark:border-blue-800 dark:bg-blue-950',
  arxiv:
    'border-purple-200 bg-purple-50 dark:border-purple-800 dark:bg-purple-950',
  pubmed:
    'border-green-200 bg-green-50 dark:border-green-800 dark:bg-green-950',
};

export default function ResearchDashboard() {
  const [currentQuery, setCurrentQuery] = useState<ResearchQuery>({
    query: '',
    sources: ['web', 'arxiv', 'pubmed'],
    status: 'idle',
    results: [],
    metrics: { totalResults: 0, processingTime: 0, sourcesQueried: 0 },
  });

  const [searchHistory, setSearchHistory] = useState<ResearchQuery[]>([]);
  const [isConnected, setIsConnected] = useState(false);

  // Check bridge connectivity
  useEffect(() => {
    const checkConnection = async () => {
      try {
        const response = await fetch('http://localhost:3001/health');
        setIsConnected(response.ok);
      } catch {
        setIsConnected(false);
      }
    };

    checkConnection();
    const interval = setInterval(checkConnection, 30000);
    return () => clearInterval(interval);
  }, []);

  const performSearch = useCallback(
    async (query: string) => {
      if (!query.trim() || !isConnected) return;

      const startTime = Date.now();
      setCurrentQuery(prev => ({
        ...prev,
        query,
        status: 'searching',
        results: [],
      }));

      try {
        // Call our production pipeline through the bridge
        const response = await fetch('http://localhost:3001/api/search', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            query,
            sources: currentQuery.sources,
            maxResults: 20,
          }),
        });

        if (!response.ok) {
          throw new Error(`Search failed: ${response.statusText}`);
        }

        const data = await response.json();
        const processingTime = Date.now() - startTime;

        const newQuery: ResearchQuery = {
          query,
          sources: currentQuery.sources,
          status: 'completed',
          results: data.results || [],
          metrics: {
            totalResults: data.results?.length || 0,
            processingTime,
            sourcesQueried: currentQuery.sources.length,
          },
        };

        setCurrentQuery(newQuery);
        setSearchHistory(prev => [newQuery, ...prev.slice(0, 9)]); // Keep last 10 searches
      } catch (error) {
        console.error('Search error:', error);
        setCurrentQuery(prev => ({
          ...prev,
          status: 'error',
          results: [],
        }));
      }
    },
    [currentQuery.sources, isConnected]
  );

  const toggleSource = (source: string) => {
    setCurrentQuery(prev => ({
      ...prev,
      sources: prev.sources.includes(source)
        ? prev.sources.filter(s => s !== source)
        : [...prev.sources, source],
    }));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    performSearch(currentQuery.query);
  };

  return (
    <div className='min-h-screen bg-gradient-to-br from-neutral-50 to-neutral-100 dark:from-neutral-950 dark:to-neutral-900 p-4 lg:p-8'>
      <div className='max-w-7xl mx-auto space-y-8'>
        {/* Header */}
        <motion.header
          className='flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between'
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <div>
            <h1 className='text-3xl font-bold tracking-tight text-neutral-900 dark:text-neutral-100 sm:text-4xl'>
              🔍 Interactive Research Dashboard
            </h1>
            <p className='text-neutral-600 dark:text-neutral-400 mt-2'>
              Multi-source research powered by production APIs
            </p>
          </div>
          <div className='flex items-center gap-3'>
            <div
              className={`px-3 py-1 rounded-full text-xs font-medium ${
                isConnected
                  ? 'bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400'
                  : 'bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-400'
              }`}
            >
              {isConnected ? '🟢 Connected' : '🔴 Disconnected'}
            </div>
          </div>
        </motion.header>

        {/* Search Interface */}
        <motion.section
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1 }}
        >
          <Card>
            <CardHeader>
              <CardTitle>Research Query</CardTitle>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleSubmit} className='space-y-4'>
                <div className='flex gap-2'>
                  <Input
                    placeholder='Enter your research query...'
                    value={currentQuery.query}
                    onChange={e =>
                      setCurrentQuery(prev => ({
                        ...prev,
                        query: e.target.value,
                      }))
                    }
                    className='flex-1'
                    disabled={currentQuery.status === 'searching'}
                  />
                  <Button
                    type='submit'
                    disabled={
                      !currentQuery.query.trim() ||
                      currentQuery.status === 'searching' ||
                      !isConnected
                    }
                    className='min-w-[100px]'
                  >
                    {currentQuery.status === 'searching' ? (
                      <div className='flex items-center gap-2'>
                        <div className='w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin' />
                        Searching
                      </div>
                    ) : (
                      'Search'
                    )}
                  </Button>
                </div>

                {/* Source Selection */}
                <div className='flex gap-2 flex-wrap'>
                  <span className='text-sm text-neutral-600 dark:text-neutral-400 self-center'>
                    Sources:
                  </span>
                  {Object.entries(sourceIcons).map(([source, icon]) => (
                    <Button
                      key={source}
                      type='button'
                      variant={
                        currentQuery.sources.includes(source)
                          ? 'default'
                          : 'outline'
                      }
                      size='sm'
                      onClick={() => toggleSource(source)}
                      className='flex items-center gap-1'
                    >
                      <span>{icon}</span>
                      <span className='capitalize'>{source}</span>
                    </Button>
                  ))}
                </div>
              </form>
            </CardContent>
          </Card>
        </motion.section>

        {/* Search Metrics */}
        <AnimatePresence>
          {currentQuery.status === 'completed' && (
            <motion.section
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.5 }}
            >
              <div className='grid grid-cols-1 gap-4 sm:grid-cols-3'>
                <Card>
                  <CardContent className='p-4'>
                    <div className='text-center'>
                      <div className='text-2xl font-bold text-blue-600 dark:text-blue-400'>
                        {currentQuery.metrics.totalResults}
                      </div>
                      <div className='text-sm text-neutral-600 dark:text-neutral-400'>
                        Results Found
                      </div>
                    </div>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className='p-4'>
                    <div className='text-center'>
                      <div className='text-2xl font-bold text-green-600 dark:text-green-400'>
                        {(currentQuery.metrics.processingTime / 1000).toFixed(
                          2
                        )}
                        s
                      </div>
                      <div className='text-sm text-neutral-600 dark:text-neutral-400'>
                        Processing Time
                      </div>
                    </div>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className='p-4'>
                    <div className='text-center'>
                      <div className='text-2xl font-bold text-purple-600 dark:text-purple-400'>
                        {currentQuery.metrics.sourcesQueried}
                      </div>
                      <div className='text-sm text-neutral-600 dark:text-neutral-400'>
                        Sources Queried
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>
            </motion.section>
          )}
        </AnimatePresence>

        {/* Search Results */}
        <AnimatePresence>
          {currentQuery.results.length > 0 && (
            <motion.section
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.5 }}
            >
              <h2 className='text-xl font-semibold mb-4'>Research Results</h2>
              <div className='grid gap-4'>
                {currentQuery.results.map((result, index) => (
                  <motion.div
                    key={result.id}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.3, delay: index * 0.1 }}
                  >
                    <Card
                      className={`${sourceColors[result.source]} border-l-4`}
                    >
                      <CardContent className='p-4'>
                        <div className='flex items-start justify-between gap-4'>
                          <div className='flex-1 min-w-0'>
                            <div className='flex items-center gap-2 mb-2'>
                              <span className='text-lg'>
                                {sourceIcons[result.source]}
                              </span>
                              <span className='text-xs px-2 py-1 rounded-full bg-neutral-200 dark:bg-neutral-700 capitalize'>
                                {result.source}
                              </span>
                              {result.confidence && (
                                <span className='text-xs px-2 py-1 rounded-full bg-blue-100 text-blue-800 dark:bg-blue-900/20 dark:text-blue-400'>
                                  {Math.round(result.confidence * 100)}%
                                  confidence
                                </span>
                              )}
                            </div>

                            <h3 className='font-semibold text-neutral-900 dark:text-neutral-100 mb-2 line-clamp-2'>
                              {result.title}
                            </h3>

                            <p className='text-sm text-neutral-600 dark:text-neutral-400 mb-3 line-clamp-3'>
                              {result.content}
                            </p>

                            {result.authors && (
                              <p className='text-xs text-neutral-500 dark:text-neutral-500 mb-2'>
                                Authors: {result.authors.join(', ')}
                              </p>
                            )}

                            {result.publishedDate && (
                              <p className='text-xs text-neutral-500 dark:text-neutral-500 mb-2'>
                                Published:{' '}
                                {new Date(
                                  result.publishedDate
                                ).toLocaleDateString()}
                              </p>
                            )}
                          </div>

                          {result.url && (
                            <Button
                              variant='outline'
                              size='sm'
                              onClick={() => window.open(result.url, '_blank')}
                              className='shrink-0'
                            >
                              View Source
                            </Button>
                          )}
                        </div>
                      </CardContent>
                    </Card>
                  </motion.div>
                ))}
              </div>
            </motion.section>
          )}
        </AnimatePresence>

        {/* Search History */}
        {searchHistory.length > 0 && (
          <motion.section
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.3 }}
          >
            <Card>
              <CardHeader>
                <CardTitle>Recent Searches</CardTitle>
              </CardHeader>
              <CardContent>
                <div className='space-y-2'>
                  {searchHistory.slice(0, 5).map((search, index) => (
                    <div
                      key={index}
                      className='flex items-center justify-between p-2 bg-neutral-50 dark:bg-neutral-800 rounded cursor-pointer hover:bg-neutral-100 dark:hover:bg-neutral-700 transition-colors'
                      onClick={() =>
                        setCurrentQuery(prev => ({
                          ...prev,
                          query: search.query,
                        }))
                      }
                    >
                      <span className='text-sm truncate'>{search.query}</span>
                      <div className='flex items-center gap-2 text-xs text-neutral-500'>
                        <span>{search.metrics.totalResults} results</span>
                        <span>•</span>
                        <span>
                          {(search.metrics.processingTime / 1000).toFixed(2)}s
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </motion.section>
        )}
      </div>
    </div>
  );
}
