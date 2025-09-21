import { useState, useEffect } from 'react';
import Head from 'next/head';
import {
  Activity,
  CheckCircle,
  XCircle,
  Clock,
  GitBranch,
  Shield,
  Server,
  Database,
  Cpu,
  Network,
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
  Sparkles
} from 'lucide-react';

interface WorkflowRun {
  id: number;
  name: string;
  status: 'success' | 'failure' | 'in_progress' | 'queued';
  conclusion: string | null;
  created_at: string;
  updated_at: string;
  html_url: string;
  head_branch: string;
}

interface SystemStatus {
  workflows: WorkflowRun[];
  lastUpdated: string;
  totalRuns: number;
  successRate: number;
  activeServices: number;
  systemHealth: 'healthy' | 'degraded' | 'critical';
}

export default function Dashboard() {
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const response = await fetch('/api/status');
        if (!response.ok) {
          throw new Error('Failed to fetch status');
        }
        const data = await response.json();
        setStatus(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    };

    fetchStatus();
    const interval = setInterval(fetchStatus, 30000); // Refresh every 30 seconds

    return () => clearInterval(interval);
  }, []);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'success':
        return <CheckCircle className="w-5 h-5 text-success-500" />;
      case 'failure':
        return <XCircle className="w-5 h-5 text-danger-500" />;
      case 'in_progress':
        return <Activity className="w-5 h-5 text-warning-500 animate-pulse" />;
      case 'queued':
        return <Clock className="w-5 h-5 text-gray-500" />;
      default:
        return <Clock className="w-5 h-5 text-gray-500" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'success':
        return 'bg-success-50 border-success-200 text-success-800';
      case 'failure':
        return 'bg-danger-50 border-danger-200 text-danger-800';
      case 'in_progress':
        return 'bg-warning-50 border-warning-200 text-warning-800';
      case 'queued':
        return 'bg-gray-50 border-gray-200 text-gray-800';
      default:
        return 'bg-gray-50 border-gray-200 text-gray-800';
    }
  };

  const formatTimeAgo = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffInMinutes = Math.floor((now.getTime() - date.getTime()) / (1000 * 60));
    
    if (diffInMinutes < 1) return 'Just now';
    if (diffInMinutes < 60) return `${diffInMinutes}m ago`;
    const diffInHours = Math.floor(diffInMinutes / 60);
    if (diffInHours < 24) return `${diffInHours}h ago`;
    const diffInDays = Math.floor(diffInHours / 24);
    return `${diffInDays}d ago`;
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-primary-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading PAKE System Dashboard...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <XCircle className="w-16 h-16 text-danger-500 mx-auto mb-4" />
          <h1 className="text-2xl font-bold text-gray-900 mb-2">Dashboard Error</h1>
          <p className="text-gray-600 mb-4">{error}</p>
          <button 
            onClick={() => window.location.reload()} 
            className="bg-primary-600 text-white px-4 py-2 rounded-lg hover:bg-primary-700"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <>
      <Head>
        <title>PAKE System Dashboard</title>
        <meta name="description" content="Enterprise Knowledge Management & AI Research Platform" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="icon" href="/favicon.ico" />
      </Head>

      <div className="min-h-screen bg-gray-50">
        {/* Header */}
        <header className="bg-white shadow-sm border-b">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between items-center py-6">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <Cpu className="w-8 h-8 text-primary-600" />
                </div>
                <div className="ml-3">
                  <h1 className="text-2xl font-bold text-gray-900">PAKE System</h1>
                  <p className="text-sm text-gray-500">Enterprise Dashboard</p>
                </div>
              </div>
              <div className="flex items-center space-x-4">
                <div className="text-sm text-gray-500">
                  Last updated: {status?.lastUpdated ? formatTimeAgo(status.lastUpdated) : 'Never'}
                </div>
                <div className={`px-3 py-1 rounded-full text-sm font-medium ${
                  status?.systemHealth === 'healthy' ? 'bg-success-100 text-success-800' :
                  status?.systemHealth === 'degraded' ? 'bg-warning-100 text-warning-800' :
                  'bg-danger-100 text-danger-800'
                }`}>
                  {status?.systemHealth?.toUpperCase() || 'UNKNOWN'}
                </div>
              </div>
            </div>
          </div>
        </header>

        {/* Main Content */}
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {/* Stats Overview */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <GitBranch className="w-8 h-8 text-primary-600" />
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-500">Total Runs</p>
                  <p className="text-2xl font-semibold text-gray-900">{status?.totalRuns || 0}</p>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <CheckCircle className="w-8 h-8 text-success-600" />
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-500">Success Rate</p>
                  <p className="text-2xl font-semibold text-gray-900">{status?.successRate || 0}%</p>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <Server className="w-8 h-8 text-warning-600" />
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-500">Active Services</p>
                  <p className="text-2xl font-semibold text-gray-900">{status?.activeServices || 0}</p>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <Shield className="w-8 h-8 text-danger-600" />
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-500">Security Status</p>
                  <p className="text-2xl font-semibold text-gray-900">SECURE</p>
                </div>
              </div>
            </div>
          </div>

          {/* Quick Actions */}
          <div className="bg-white rounded-lg shadow mb-8">
            <div className="px-6 py-4 border-b border-gray-200">
              <h2 className="text-lg font-medium text-gray-900 flex items-center">
                <Sparkles className="w-5 h-5 mr-2" />
                PAKE System Features
              </h2>
            </div>
            <div className="p-6">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <a
                  href="/operational"
                  className="block p-4 border border-primary-200 rounded-lg hover:border-primary-400 hover:bg-primary-50 transition-colors"
                >
                  <div className="flex items-center mb-2">
                    <Brain className="w-6 h-6 text-primary-600 mr-2" />
                    <h3 className="font-medium text-gray-900">Operational Dashboard</h3>
                  </div>
                  <p className="text-sm text-gray-600">Test live ingestion, AI analysis, and knowledge search capabilities</p>
                </a>

                <div className="p-4 border border-success-200 rounded-lg bg-success-50">
                  <div className="flex items-center mb-2">
                    <Search className="w-6 h-6 text-success-600 mr-2" />
                    <h3 className="font-medium text-gray-900">Multi-Source Research</h3>
                  </div>
                  <p className="text-sm text-gray-600">Research across Web, ArXiv, PubMed in &lt;1 second</p>
                </div>

                <div className="p-4 border border-warning-200 rounded-lg bg-warning-50">
                  <div className="flex items-center mb-2">
                    <TrendingUp className="w-6 h-6 text-warning-600 mr-2" />
                    <h3 className="font-medium text-gray-900">Trend Intelligence</h3>
                  </div>
                  <p className="text-sm text-gray-600">Real-time trend analysis and investment mapping</p>
                </div>
              </div>
            </div>
          </div>

          {/* Recent Workflow Runs */}
          <div className="bg-white rounded-lg shadow">
            <div className="px-6 py-4 border-b border-gray-200">
              <h2 className="text-lg font-medium text-gray-900">Recent Workflow Runs</h2>
            </div>
            <div className="divide-y divide-gray-200">
              {status?.workflows?.slice(0, 10).map((workflow) => (
                <div key={workflow.id} className="px-6 py-4 hover:bg-gray-50">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-4">
                      {getStatusIcon(workflow.conclusion || workflow.status)}
                      <div>
                        <p className="text-sm font-medium text-gray-900">{workflow.name}</p>
                        <p className="text-sm text-gray-500">
                          <GitBranch className="w-4 h-4 inline mr-1" />
                          {workflow.head_branch}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center space-x-4">
                      <span className={`px-2 py-1 text-xs font-medium rounded-full ${getStatusColor(workflow.conclusion || workflow.status)}`}>
                        {workflow.conclusion || workflow.status}
                      </span>
                      <span className="text-sm text-gray-500">
                        {formatTimeAgo(workflow.created_at)}
                      </span>
                      <a
                        href={workflow.html_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-primary-600 hover:text-primary-700 text-sm font-medium"
                      >
                        View →
                      </a>
                    </div>
                  </div>
                </div>
              )) || (
                <div className="px-6 py-8 text-center text-gray-500">
                  No workflow runs found
                </div>
              )}
            </div>
          </div>
        </main>
      </div>
    </>
  );
}
