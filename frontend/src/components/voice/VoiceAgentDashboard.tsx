'use client';

import { useState } from 'react';
import {
  Mic,
  MicOff,
  Play,
  Pause,
  Phone,
  PhoneOff,
  Users,
  Clock,
  MessageSquare,
  BarChart3,
  Settings,
  Volume2,
  VolumeX,
} from 'lucide-react';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Button } from '@/components/ui/button';

interface VoiceAgentStats {
  totalCalls: number;
  activeCalls: number;
  avgCallDuration: string;
  successRate: number;
  responsiveness: string;
}

interface ActiveCall {
  id: string;
  agentName: string;
  callerName: string;
  duration: string;
  status: 'active' | 'on-hold' | 'transferring';
  sentiment: 'positive' | 'neutral' | 'negative';
}

function VoiceMetricsCard({
  title,
  value,
  icon: Icon,
  trend,
  color = 'blue',
}: {
  title: string;
  value: string;
  icon: React.ElementType;
  trend?: string;
  color?: string;
}) {
  const colorClasses = {
    blue: 'text-blue-600 bg-blue-50',
    green: 'text-green-600 bg-green-50',
    purple: 'text-purple-600 bg-purple-50',
    orange: 'text-orange-600 bg-orange-50',
  };

  return (
    <Card>
      <CardHeader className='flex flex-row items-center justify-between space-y-0 pb-2'>
        <CardTitle className='text-sm font-medium'>{title}</CardTitle>
        <div
          className={`h-8 w-8 rounded-full flex items-center justify-center ${colorClasses[color as keyof typeof colorClasses]}`}
        >
          <Icon className='h-4 w-4' />
        </div>
      </CardHeader>
      <CardContent>
        <div className='text-2xl font-bold'>{value}</div>
        {trend && <p className='text-xs text-gray-500 mt-1'>{trend}</p>}
      </CardContent>
    </Card>
  );
}

function ActiveCallsPanel({ calls }: { calls: ActiveCall[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Active Calls</CardTitle>
        <CardDescription>Real-time voice agent conversations</CardDescription>
      </CardHeader>
      <CardContent>
        <div className='space-y-4'>
          {calls.length === 0 ? (
            <div className='text-center py-8 text-gray-500'>
              <Phone className='h-12 w-12 mx-auto mb-4 text-gray-300' />
              <p>No active calls at the moment</p>
            </div>
          ) : (
            calls.map(call => (
              <div
                key={call.id}
                className='flex items-center justify-between p-4 border border-gray-200 rounded-lg'
              >
                <div className='flex items-center space-x-3'>
                  <div
                    className={`w-3 h-3 rounded-full ${
                      call.status === 'active'
                        ? 'bg-green-500 animate-pulse'
                        : call.status === 'on-hold'
                          ? 'bg-yellow-500'
                          : 'bg-blue-500'
                    }`}
                  />
                  <div>
                    <div className='font-medium text-sm'>{call.agentName}</div>
                    <div className='text-xs text-gray-500'>
                      with {call.callerName}
                    </div>
                  </div>
                </div>
                <div className='flex items-center space-x-3'>
                  <div className='text-right'>
                    <div className='text-sm font-medium'>{call.duration}</div>
                    <div
                      className={`text-xs ${
                        call.sentiment === 'positive'
                          ? 'text-green-600'
                          : call.sentiment === 'neutral'
                            ? 'text-gray-600'
                            : 'text-red-600'
                      }`}
                    >
                      {call.sentiment}
                    </div>
                  </div>
                  <Button variant='ghost' size='sm'>
                    <Volume2 className='h-4 w-4' />
                  </Button>
                </div>
              </div>
            ))
          )}
        </div>
      </CardContent>
    </Card>
  );
}

function VoiceAgentControls() {
  const [isRecording, setIsRecording] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isMuted, setIsMuted] = useState(false);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Voice Agent Controls</CardTitle>
        <CardDescription>Manage voice agent operations</CardDescription>
      </CardHeader>
      <CardContent>
        <div className='grid grid-cols-2 md:grid-cols-4 gap-4'>
          <Button
            variant={isRecording ? 'destructive' : 'outline'}
            onClick={() => setIsRecording(!isRecording)}
            className='flex flex-col items-center space-y-2 h-20'
          >
            {isRecording ? (
              <MicOff className='h-6 w-6' />
            ) : (
              <Mic className='h-6 w-6' />
            )}
            <span className='text-xs'>
              {isRecording ? 'Stop Recording' : 'Start Recording'}
            </span>
          </Button>

          <Button
            variant={isPlaying ? 'secondary' : 'outline'}
            onClick={() => setIsPlaying(!isPlaying)}
            className='flex flex-col items-center space-y-2 h-20'
          >
            {isPlaying ? (
              <Pause className='h-6 w-6' />
            ) : (
              <Play className='h-6 w-6' />
            )}
            <span className='text-xs'>{isPlaying ? 'Pause' : 'Play'}</span>
          </Button>

          <Button
            variant={isMuted ? 'destructive' : 'outline'}
            onClick={() => setIsMuted(!isMuted)}
            className='flex flex-col items-center space-y-2 h-20'
          >
            {isMuted ? (
              <VolumeX className='h-6 w-6' />
            ) : (
              <Volume2 className='h-6 w-6' />
            )}
            <span className='text-xs'>{isMuted ? 'Unmute' : 'Mute'}</span>
          </Button>

          <Button
            variant='outline'
            className='flex flex-col items-center space-y-2 h-20'
          >
            <Settings className='h-6 w-6' />
            <span className='text-xs'>Configure</span>
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

function AgentPerformanceChart() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Agent Performance</CardTitle>
        <CardDescription>
          Voice agent performance metrics over time
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className='h-64 flex items-center justify-center border-2 border-dashed border-gray-200 rounded-lg'>
          <div className='text-center'>
            <BarChart3 className='h-12 w-12 text-gray-400 mx-auto mb-4' />
            <p className='text-gray-500'>Performance Analytics Chart</p>
            <p className='text-sm text-gray-400'>
              Success rate trending upward
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function ConversationHistory() {
  const conversations = [
    {
      id: '1',
      caller: 'John Doe',
      agent: 'Sarah AI',
      duration: '4:32',
      outcome: 'Resolved',
      sentiment: 'positive',
      timestamp: '2 hours ago',
    },
    {
      id: '2',
      caller: 'Jane Smith',
      agent: 'Marcus AI',
      duration: '2:15',
      outcome: 'Transferred',
      sentiment: 'neutral',
      timestamp: '3 hours ago',
    },
    {
      id: '3',
      caller: 'Bob Johnson',
      agent: 'Elena AI',
      duration: '6:45',
      outcome: 'Resolved',
      sentiment: 'positive',
      timestamp: '4 hours ago',
    },
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle>Recent Conversations</CardTitle>
        <CardDescription>Latest voice agent interactions</CardDescription>
      </CardHeader>
      <CardContent>
        <div className='space-y-3'>
          {conversations.map(conv => (
            <div
              key={conv.id}
              className='flex items-center justify-between p-3 border border-gray-100 rounded-lg hover:bg-gray-50 transition-colors'
            >
              <div className='flex items-center space-x-3'>
                <MessageSquare className='h-5 w-5 text-gray-400' />
                <div>
                  <div className='font-medium text-sm'>{conv.caller}</div>
                  <div className='text-xs text-gray-500'>
                    Agent: {conv.agent}
                  </div>
                </div>
              </div>
              <div className='text-right'>
                <div className='text-sm'>{conv.duration}</div>
                <div
                  className={`text-xs ${
                    conv.sentiment === 'positive'
                      ? 'text-green-600'
                      : conv.sentiment === 'neutral'
                        ? 'text-gray-600'
                        : 'text-red-600'
                  }`}
                >
                  {conv.outcome}
                </div>
                <div className='text-xs text-gray-400'>{conv.timestamp}</div>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

export function VoiceAgentDashboard() {
  const stats: VoiceAgentStats = {
    totalCalls: 247,
    activeCalls: 3,
    avgCallDuration: '4:32',
    successRate: 94.2,
    responsiveness: '1.2s',
  };

  const activeCalls: ActiveCall[] = [
    {
      id: '1',
      agentName: 'Sarah AI Assistant',
      callerName: 'Customer Support',
      duration: '3:45',
      status: 'active',
      sentiment: 'positive',
    },
    {
      id: '2',
      agentName: 'Marcus AI Helper',
      callerName: 'Technical Query',
      duration: '1:23',
      status: 'active',
      sentiment: 'neutral',
    },
  ];

  return (
    <div className='space-y-6 p-6'>
      {/* Header */}
      <div className='flex items-center justify-between'>
        <div>
          <h1 className='text-3xl font-bold text-gray-900'>
            Voice Agent Dashboard
          </h1>
          <p className='text-gray-600 mt-2'>
            Monitor and manage AI voice agents in real-time
          </p>
        </div>
        <div className='flex space-x-2'>
          <Button variant='outline'>
            <Phone className='h-4 w-4 mr-2' />
            Test Call
          </Button>
          <Button>
            <Settings className='h-4 w-4 mr-2' />
            Configure
          </Button>
        </div>
      </div>

      {/* Metrics Grid */}
      <div className='grid gap-6 md:grid-cols-2 lg:grid-cols-5'>
        <VoiceMetricsCard
          title='Total Calls'
          value={stats.totalCalls.toString()}
          icon={Phone}
          trend='↑ 15% from yesterday'
          color='blue'
        />
        <VoiceMetricsCard
          title='Active Calls'
          value={stats.activeCalls.toString()}
          icon={Users}
          trend='Real-time'
          color='green'
        />
        <VoiceMetricsCard
          title='Avg Duration'
          value={stats.avgCallDuration}
          icon={Clock}
          trend='↓ 12s from average'
          color='purple'
        />
        <VoiceMetricsCard
          title='Success Rate'
          value={`${stats.successRate}%`}
          icon={BarChart3}
          trend='↑ 2.1% this week'
          color='green'
        />
        <VoiceMetricsCard
          title='Response Time'
          value={stats.responsiveness}
          icon={MessageSquare}
          trend='Optimal performance'
          color='orange'
        />
      </div>

      {/* Control Panel */}
      <VoiceAgentControls />

      {/* Main Content Grid */}
      <div className='grid gap-6 lg:grid-cols-3'>
        {/* Active Calls - Takes 2 columns */}
        <div className='lg:col-span-2'>
          <ActiveCallsPanel calls={activeCalls} />
        </div>

        {/* Conversation History */}
        <ConversationHistory />
      </div>

      {/* Performance Chart */}
      <AgentPerformanceChart />
    </div>
  );
}
