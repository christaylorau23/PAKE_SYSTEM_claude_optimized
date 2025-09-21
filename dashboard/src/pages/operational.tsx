import { useState, useEffect } from 'react';
import Head from 'next/head';
import {
  Search,
  Brain,
  Zap,
  Globe,
  TrendingUp,
  FileText,
  Users,
  Lock,
  BarChart3,
  RefreshCw,
  PlayCircle,
  Settings,
  Layers,
  Sparkles,
  CheckCircle,
  XCircle,
  Clock,
  Activity,
  Database,
  Server,
  Shield,
  Network,
  Cpu
} from 'lucide-react';

interface PAKESystemStatus {
  ingestionOrchestrator: 'operational' | 'degraded' | 'offline';
  cacheService: 'operational' | 'degraded' | 'offline';
  authService: 'operational' | 'degraded' | 'offline';
  searchService: 'operational' | 'degraded' | 'offline';
  totalRequests: number;
  cacheHitRate: number;
  avgResponseTime: number;
  activeUsers: number;
}

interface IngestionTest {
  id: string;
  source: 'web' | 'arxiv' | 'pubmed' | 'social';
  query: string;
  status: 'running' | 'completed' | 'failed';
  results?: number;
  duration?: number;
}

interface KnowledgeDemo {
  id: string;
  title: string;
  description: string;
  endpoint: string;
  method: 'GET' | 'POST';
  status: 'available' | 'testing' | 'unavailable';
}

export default function OperationalDashboard() {
  const [systemStatus, setSystemStatus] = useState<PAKESystemStatus>({
    ingestionOrchestrator: 'operational',
    cacheService: 'operational',
    authService: 'operational',
    searchService: 'operational',
    totalRequests: 15847,
    cacheHitRate: 94.2,
    avgResponseTime: 0.12,
    activeUsers: 23
  });

  const [ingestionTests, setIngestionTests] = useState<IngestionTest[]>([
    { id: '1', source: 'web', query: 'AI automation tools', status: 'completed', results: 12, duration: 0.8 },
    { id: '2', source: 'arxiv', query: 'machine learning optimization', status: 'completed', results: 8, duration: 0.6 },
    { id: '3', source: 'pubmed', query: 'neural networks medical applications', status: 'running' },
  ]);

  const [knowledgeDemos] = useState<KnowledgeDemo[]>([
    {
      id: '1',
      title: 'Multi-Source Research',
      description: 'Research any topic across Web, ArXiv, and PubMed simultaneously',
      endpoint: '/api/research',
      method: 'POST',
      status: 'available'
    },
    {
      id: '2',
      title: 'Semantic Knowledge Search',
      description: 'AI-powered semantic search across ingested knowledge base',
      endpoint: '/api/search',
      method: 'GET',
      status: 'available'
    },
    {
      id: '3',
      title: 'Content Analysis & Summarization',
      description: 'Intelligent content analysis with automatic summarization',
      endpoint: '/api/analyze',
      method: 'POST',
      status: 'available'
    },
    {
      id: '4',
      title: 'Real-time Trend Intelligence',
      description: 'Live trend analysis and investment opportunity mapping',
      endpoint: '/api/trends',
      method: 'GET',
      status: 'testing'
    },
    {
      id: '5',
      title: 'Knowledge Graph Explorer',
      description: 'Interactive knowledge graph visualization and navigation',
      endpoint: '/api/knowledge-graph',
      method: 'GET',
      status: 'available'
    },
    {
      id: '6',
      title: 'Enterprise Authentication',
      description: 'JWT-based multi-tenant authentication system',
      endpoint: '/api/auth',
      method: 'POST',
      status: 'available'
    }
  ]);

  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [isSearching, setIsSearching] = useState(false);

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;

    setIsSearching(true);
    try {
      // Simulate API call to PAKE System
      await new Promise(resolve => setTimeout(resolve, 1200));

      setSearchResults([
        {
          id: '1',
          title: 'AI-Powered Knowledge Management Systems',
          source: 'ArXiv',
          snippet: 'Comprehensive study on enterprise AI knowledge management with multi-source ingestion capabilities...',
          relevance: 0.95,
          timestamp: new Date().toISOString()
        },
        {
          id: '2',
          title: 'Web Scraping for Research Automation',
          source: 'Web',
          snippet: 'Advanced techniques for automated research data collection and analysis using modern web scraping...',
          relevance: 0.89,
          timestamp: new Date().toISOString()
        },
        {
          id: '3',
          title: 'Semantic Search in Medical Literature',
          source: 'PubMed',
          snippet: 'Novel approaches to semantic search and knowledge discovery in biomedical literature databases...',
          relevance: 0.87,
          timestamp: new Date().toISOString()
        }
      ]);
    } catch (error) {
      console.error('Search failed:', error);
    } finally {
      setIsSearching(false);
    }
  };

  const runIngestionTest = async (source: string) => {
    const newTest: IngestionTest = {
      id: Date.now().toString(),
      source: source as any,
      query: `Test query for ${source}`,
      status: 'running'
    };

    setIngestionTests(prev => [newTest, ...prev]);

    // Simulate ingestion test
    setTimeout(() => {
      setIngestionTests(prev => prev.map(test =>
        test.id === newTest.id
          ? { ...test, status: 'completed', results: Math.floor(Math.random() * 15) + 5, duration: Math.random() * 2 + 0.5 }
          : test
      ));
    }, 2000 + Math.random() * 3000);
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'operational':
      case 'completed':
      case 'available':
        return <CheckCircle className="w-5 h-5 text-success-500" />;
      case 'degraded':
      case 'testing':
        return <Clock className="w-5 h-5 text-warning-500" />;
      case 'running':
        return <Activity className="w-5 h-5 text-primary-500 animate-pulse" />;
      case 'offline':
      case 'failed':
      case 'unavailable':
        return <XCircle className="w-5 h-5 text-danger-500" />;
      default:
        return <Clock className="w-5 h-5 text-gray-500" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'operational':
      case 'completed':
      case 'available':
        return 'bg-success-50 border-success-200 text-success-800';
      case 'degraded':
      case 'testing':
        return 'bg-warning-50 border-warning-200 text-warning-800';
      case 'running':
        return 'bg-primary-50 border-primary-200 text-primary-800';
      case 'offline':
      case 'failed':
      case 'unavailable':
        return 'bg-danger-50 border-danger-200 text-danger-800';
      default:
        return 'bg-gray-50 border-gray-200 text-gray-800';
    }
  };

  return (
    <>
      <Head>
        <title>PAKE System - Operational Dashboard</title>
        <meta name="description" content="Comprehensive operational interface for PAKE System enterprise features" />
      </Head>

      <div className="min-h-screen bg-gray-50">
        {/* Header */}
        <header className="bg-white shadow-sm border-b">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between items-center py-6">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <Layers className="w-8 h-8 text-primary-600" />
                </div>
                <div className="ml-3">
                  <h1 className="text-2xl font-bold gradient-text">PAKE System</h1>
                  <p className="text-sm text-gray-500">Operational Dashboard</p>
                </div>
              </div>
              <div className="flex items-center space-x-4">
                <span className="text-sm text-gray-500">
                  Live System Status
                </span>
                <div className="px-3 py-1 rounded-full text-sm font-medium bg-success-100 text-success-800">
                  ALL SYSTEMS OPERATIONAL
                </div>
              </div>
            </div>
          </div>
        </header>

        {/* Main Content */}
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">

          {/* System Status Overview */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <Server className="w-8 h-8 text-primary-600" />
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-500">Total Requests</p>
                  <p className="text-2xl font-semibold text-gray-900">{systemStatus.totalRequests.toLocaleString()}</p>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <Zap className="w-8 h-8 text-success-600" />
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-500">Cache Hit Rate</p>
                  <p className="text-2xl font-semibold text-gray-900">{systemStatus.cacheHitRate}%</p>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <Zap className="w-8 h-8 text-warning-600" />
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-500">Avg Response</p>
                  <p className="text-2xl font-semibold text-gray-900">{systemStatus.avgResponseTime}s</p>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <Users className="w-8 h-8 text-primary-600" />
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-500">Active Users</p>
                  <p className="text-2xl font-semibold text-gray-900">{systemStatus.activeUsers}</p>
                </div>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">

            {/* Live Knowledge Search */}
            <div className="bg-white rounded-lg shadow">
              <div className="px-6 py-4 border-b border-gray-200">
                <h2 className="text-lg font-medium text-gray-900 flex items-center">
                  <Search className="w-5 h-5 mr-2" />
                  Live Knowledge Search
                </h2>
              </div>
              <div className="p-6">
                <div className="flex space-x-4 mb-4">
                  <input
                    type="text"
                    placeholder="Search across all knowledge sources..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="flex-1 border border-gray-300 rounded-lg px-4 py-2 focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                    onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
                  />
                  <button
                    onClick={handleSearch}
                    disabled={isSearching || !searchQuery.trim()}
                    className="px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 flex items-center"
                  >
                    {isSearching ? (
                      <RefreshCw className="w-4 h-4 animate-spin" />
                    ) : (
                      <Search className="w-4 h-4" />
                    )}
                  </button>
                </div>

                <div className="space-y-3 max-h-64 overflow-y-auto">
                  {searchResults.map((result) => (
                    <div key={result.id} className="border border-gray-200 rounded-lg p-3 hover:bg-gray-50">
                      <div className="flex justify-between items-start mb-1">
                        <h4 className="font-medium text-gray-900">{result.title}</h4>
                        <span className="text-xs px-2 py-1 bg-primary-100 text-primary-800 rounded">
                          {result.source}
                        </span>
                      </div>
                      <p className="text-sm text-gray-600 mb-2">{result.snippet}</p>
                      <div className="flex justify-between text-xs text-gray-500">
                        <span>Relevance: {(result.relevance * 100).toFixed(1)}%</span>
                        <span>{new Date(result.timestamp).toLocaleTimeString()}</span>
                      </div>
                    </div>
                  ))}
                  {searchResults.length === 0 && !isSearching && (
                    <div className="text-center text-gray-500 py-8">
                      Enter a search query to test the knowledge search system
                    </div>
                  )}
                  {isSearching && (
                    <div className="text-center text-gray-500 py-8">
                      <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2" />
                      Searching across all knowledge sources...
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Ingestion Testing */}
            <div className="bg-white rounded-lg shadow">
              <div className="px-6 py-4 border-b border-gray-200">
                <h2 className="text-lg font-medium text-gray-900 flex items-center">
                  <Globe className="w-5 h-5 mr-2" />
                  Live Ingestion Testing
                </h2>
              </div>
              <div className="p-6">
                <div className="grid grid-cols-2 gap-3 mb-4">
                  <button
                    onClick={() => runIngestionTest('web')}
                    className="px-4 py-2 bg-primary-100 text-primary-800 rounded-lg hover:bg-primary-200 flex items-center justify-center"
                  >
                    <Globe className="w-4 h-4 mr-2" />
                    Test Web
                  </button>
                  <button
                    onClick={() => runIngestionTest('arxiv')}
                    className="px-4 py-2 bg-success-100 text-success-800 rounded-lg hover:bg-success-200 flex items-center justify-center"
                  >
                    <FileText className="w-4 h-4 mr-2" />
                    Test ArXiv
                  </button>
                  <button
                    onClick={() => runIngestionTest('pubmed')}
                    className="px-4 py-2 bg-warning-100 text-warning-800 rounded-lg hover:bg-warning-200 flex items-center justify-center"
                  >
                    <Database className="w-4 h-4 mr-2" />
                    Test PubMed
                  </button>
                  <button
                    onClick={() => runIngestionTest('social')}
                    className="px-4 py-2 bg-danger-100 text-danger-800 rounded-lg hover:bg-danger-200 flex items-center justify-center"
                  >
                    <TrendingUp className="w-4 h-4 mr-2" />
                    Test Social
                  </button>
                </div>

                <div className="space-y-2 max-h-64 overflow-y-auto">
                  {ingestionTests.slice(0, 10).map((test) => (
                    <div key={test.id} className="flex justify-between items-center p-3 border border-gray-200 rounded-lg">
                      <div className="flex items-center space-x-3">
                        {getStatusIcon(test.status)}
                        <div>
                          <p className="text-sm font-medium text-gray-900">{test.source.toUpperCase()}</p>
                          <p className="text-xs text-gray-500">{test.query}</p>
                        </div>
                      </div>
                      <div className="text-right text-xs text-gray-500">
                        {test.results && <p>{test.results} results</p>}
                        {test.duration && <p>{test.duration.toFixed(2)}s</p>}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* PAKE System Capabilities Showcase */}
          <div className="bg-white rounded-lg shadow mb-8">
            <div className="px-6 py-4 border-b border-gray-200">
              <h2 className="text-lg font-medium text-gray-900 flex items-center">
                <Brain className="w-5 h-5 mr-2" />
                PAKE System Capabilities Demo
              </h2>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 p-6">
              {knowledgeDemos.map((demo) => (
                <div key={demo.id} className="border border-gray-200 rounded-lg p-4 hover:border-primary-300 transition-colors">
                  <div className="flex justify-between items-start mb-3">
                    <h3 className="font-medium text-gray-900">{demo.title}</h3>
                    {getStatusIcon(demo.status)}
                  </div>
                  <p className="text-sm text-gray-600 mb-3">{demo.description}</p>
                  <div className="flex justify-between items-center">
                    <span className={`px-2 py-1 text-xs font-medium rounded ${getStatusColor(demo.status)}`}>
                      {demo.status}
                    </span>
                    <div className="text-xs text-gray-500">
                      <span className="font-mono">{demo.method}</span> {demo.endpoint}
                    </div>
                  </div>
                  <button className="w-full mt-3 px-4 py-2 bg-primary-50 text-primary-700 rounded-lg hover:bg-primary-100 flex items-center justify-center">
                    <PlayCircle className="w-4 h-4 mr-2" />
                    Test API
                  </button>
                </div>
              ))}
            </div>
          </div>

          {/* System Services Status */}
          <div className="bg-white rounded-lg shadow">
            <div className="px-6 py-4 border-b border-gray-200">
              <h2 className="text-lg font-medium text-gray-900 flex items-center">
                <Activity className="w-5 h-5 mr-2" />
                System Services Status
              </h2>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 p-6">
              <div className="text-center">
                <div className="flex justify-center mb-2">
                  <Layers className="w-8 h-8 text-primary-600" />
                </div>
                <h3 className="font-medium text-gray-900 mb-1">Ingestion Orchestrator</h3>
                <div className="flex justify-center">
                  {getStatusIcon(systemStatus.ingestionOrchestrator)}
                </div>
                <span className={`inline-block px-2 py-1 text-xs rounded mt-2 ${getStatusColor(systemStatus.ingestionOrchestrator)}`}>
                  {systemStatus.ingestionOrchestrator}
                </span>
              </div>

              <div className="text-center">
                <div className="flex justify-center mb-2">
                  <Database className="w-8 h-8 text-success-600" />
                </div>
                <h3 className="font-medium text-gray-900 mb-1">Cache Service</h3>
                <div className="flex justify-center">
                  {getStatusIcon(systemStatus.cacheService)}
                </div>
                <span className={`inline-block px-2 py-1 text-xs rounded mt-2 ${getStatusColor(systemStatus.cacheService)}`}>
                  {systemStatus.cacheService}
                </span>
              </div>

              <div className="text-center">
                <div className="flex justify-center mb-2">
                  <Lock className="w-8 h-8 text-warning-600" />
                </div>
                <h3 className="font-medium text-gray-900 mb-1">Auth Service</h3>
                <div className="flex justify-center">
                  {getStatusIcon(systemStatus.authService)}
                </div>
                <span className={`inline-block px-2 py-1 text-xs rounded mt-2 ${getStatusColor(systemStatus.authService)}`}>
                  {systemStatus.authService}
                </span>
              </div>

              <div className="text-center">
                <div className="flex justify-center mb-2">
                  <Search className="w-8 h-8 text-danger-600" />
                </div>
                <h3 className="font-medium text-gray-900 mb-1">Search Service</h3>
                <div className="flex justify-center">
                  {getStatusIcon(systemStatus.searchService)}
                </div>
                <span className={`inline-block px-2 py-1 text-xs rounded mt-2 ${getStatusColor(systemStatus.searchService)}`}>
                  {systemStatus.searchService}
                </span>
              </div>
            </div>
          </div>

        </main>
      </div>
    </>
  );
}