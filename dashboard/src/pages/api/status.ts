import { NextApiRequest, NextApiResponse } from 'next';

interface WorkflowRun {
  id: number;
  name: string;
  status: string;
  conclusion: string | null;
  created_at: string;
  updated_at: string;
  html_url: string;
  head_branch: string;
}

interface GitHubWorkflowResponse {
  workflow_runs: WorkflowRun[];
}

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  try {
    const repo = process.env.GITHUB_REPO || 'christaylorau23/PAKE-System';
    const token = process.env.GITHUB_TOKEN;

    if (!token) {
      // Return mock data for demo purposes when token is not available
      const mockStatus = {
        workflows: [
          {
            id: 123456789,
            name: 'CI/CD Pipeline',
            status: 'completed',
            conclusion: 'success',
            created_at: new Date(Date.now() - 3600000).toISOString(),
            updated_at: new Date(Date.now() - 3400000).toISOString(),
            html_url: 'https://github.com/christaylorau23/PAKE-System/actions/runs/123456789',
            head_branch: 'main'
          },
          {
            id: 123456788,
            name: 'Security Audit',
            status: 'completed',
            conclusion: 'success',
            created_at: new Date(Date.now() - 7200000).toISOString(),
            updated_at: new Date(Date.now() - 6800000).toISOString(),
            html_url: 'https://github.com/christaylorau23/PAKE-System/actions/runs/123456788',
            head_branch: 'main'
          },
          {
            id: 123456787,
            name: 'Build & Test',
            status: 'completed',
            conclusion: 'success',
            created_at: new Date(Date.now() - 10800000).toISOString(),
            updated_at: new Date(Date.now() - 10200000).toISOString(),
            html_url: 'https://github.com/christaylorau23/PAKE-System/actions/runs/123456787',
            head_branch: 'feature/dashboard-enhancement'
          }
        ],
        lastUpdated: new Date().toISOString(),
        totalRuns: 3,
        successRate: 100,
        activeServices: 12,
        systemHealth: 'healthy'
      };
      return res.status(200).json(mockStatus);
    }

    // Fetch recent workflow runs
    const workflowResponse = await fetch(
      `https://api.github.com/repos/${repo}/actions/runs?per_page=20`,
      {
        headers: {
          'Authorization': `token ${token}`,
          'Accept': 'application/vnd.github.v3+json',
        },
      }
    );

    if (!workflowResponse.ok) {
      throw new Error(`GitHub API error: ${workflowResponse.status}`);
    }

    const workflowData: GitHubWorkflowResponse = await workflowResponse.json();
    
    // Process workflow data
    const workflows = workflowData.workflow_runs.map((run) => ({
      id: run.id,
      name: run.name,
      status: run.status,
      conclusion: run.conclusion,
      created_at: run.created_at,
      updated_at: run.updated_at,
      html_url: run.html_url,
      head_branch: run.head_branch,
    }));

    // Calculate statistics
    const totalRuns = workflows.length;
    const successfulRuns = workflows.filter(w => w.conclusion === 'success').length;
    const successRate = totalRuns > 0 ? Math.round((successfulRuns / totalRuns) * 100) : 0;
    
    // Determine system health
    const recentRuns = workflows.slice(0, 5);
    const recentFailures = recentRuns.filter(w => w.conclusion === 'failure').length;
    const systemHealth = recentFailures === 0 ? 'healthy' : 
                        recentFailures <= 2 ? 'degraded' : 'critical';

    // Mock active services count (in a real implementation, this would come from your service registry)
    const activeServices = 12; // PAKE System services

    const status = {
      workflows,
      lastUpdated: new Date().toISOString(),
      totalRuns,
      successRate,
      activeServices,
      systemHealth,
    };

    res.status(200).json(status);
  } catch (error) {
    console.error('Error fetching status:', error);
    res.status(500).json({ 
      error: 'Failed to fetch system status',
      details: error instanceof Error ? error.message : 'Unknown error'
    });
  }
}
