'use client';

import { useState } from 'react';
import {
  Video,
  Upload,
  Play,
  Pause,
  Download,
  Settings,
  Image,
  Mic,
  FileText,
  Clock,
  CheckCircle,
  AlertCircle,
  Loader2,
  Eye,
  Trash2,
} from 'lucide-react';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

interface VideoProject {
  id: string;
  title: string;
  status: 'draft' | 'processing' | 'completed' | 'failed';
  duration: string;
  createdAt: string;
  thumbnail: string;
  provider: 'D-ID' | 'HeyGen';
}

interface GenerationJob {
  id: string;
  title: string;
  status: 'queued' | 'processing' | 'completed' | 'failed';
  progress: number;
  estimatedTime: string;
  provider: 'D-ID' | 'HeyGen';
}

function ProjectCard({ project }: { project: VideoProject }) {
  const statusStyles = {
    draft: { bg: 'bg-gray-100', text: 'text-gray-800', icon: FileText },
    processing: { bg: 'bg-blue-100', text: 'text-blue-800', icon: Loader2 },
    completed: {
      bg: 'bg-green-100',
      text: 'text-green-800',
      icon: CheckCircle,
    },
    failed: { bg: 'bg-red-100', text: 'text-red-800', icon: AlertCircle },
  };

  const style = statusStyles[project.status];
  const StatusIcon = style.icon;

  return (
    <Card className='group hover:shadow-md transition-shadow'>
      <div className='relative'>
        <div className='aspect-video bg-gray-100 rounded-t-lg flex items-center justify-center overflow-hidden'>
          {project.thumbnail ? (
            <img
              src={project.thumbnail}
              alt={project.title}
              className='w-full h-full object-cover'
            />
          ) : (
            <Video className='h-12 w-12 text-gray-400' />
          )}
          {project.status === 'completed' && (
            <div className='absolute inset-0 bg-black/50 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity'>
              <Button variant='secondary' size='sm'>
                <Play className='h-4 w-4 mr-2' />
                Preview
              </Button>
            </div>
          )}
        </div>

        <div
          className={`absolute top-2 right-2 px-2 py-1 rounded-full text-xs font-medium ${style.bg} ${style.text}`}
        >
          <StatusIcon className='h-3 w-3 inline mr-1' />
          {project.status}
        </div>
      </div>

      <CardContent className='p-4'>
        <h3 className='font-semibold text-sm mb-2 truncate'>{project.title}</h3>
        <div className='flex items-center justify-between text-xs text-gray-500'>
          <span>{project.provider}</span>
          <span>{project.createdAt}</span>
        </div>
        <div className='flex items-center justify-between mt-3'>
          <span className='text-xs text-gray-500'>{project.duration}</span>
          <div className='flex space-x-1'>
            <Button variant='ghost' size='sm'>
              <Eye className='h-3 w-3' />
            </Button>
            <Button variant='ghost' size='sm'>
              <Download className='h-3 w-3' />
            </Button>
            <Button variant='ghost' size='sm'>
              <Trash2 className='h-3 w-3' />
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function GenerationQueue({ jobs }: { jobs: GenerationJob[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Generation Queue</CardTitle>
        <CardDescription>Active video generation jobs</CardDescription>
      </CardHeader>
      <CardContent>
        <div className='space-y-4'>
          {jobs.length === 0 ? (
            <div className='text-center py-8 text-gray-500'>
              <Clock className='h-12 w-12 mx-auto mb-4 text-gray-300' />
              <p>No active generation jobs</p>
            </div>
          ) : (
            jobs.map(job => (
              <div
                key={job.id}
                className='flex items-center justify-between p-4 border border-gray-200 rounded-lg'
              >
                <div className='flex-1'>
                  <div className='flex items-center justify-between mb-2'>
                    <span className='font-medium text-sm'>{job.title}</span>
                    <span className='text-xs text-gray-500'>
                      {job.provider}
                    </span>
                  </div>

                  {job.status === 'processing' && (
                    <div className='space-y-2'>
                      <div className='flex items-center justify-between text-xs'>
                        <span>{job.progress}% complete</span>
                        <span>ETA: {job.estimatedTime}</span>
                      </div>
                      <div className='w-full bg-gray-200 rounded-full h-2'>
                        <div
                          className='bg-blue-500 h-2 rounded-full transition-all duration-300'
                          style={{ width: `${job.progress}%` }}
                        />
                      </div>
                    </div>
                  )}

                  {job.status === 'queued' && (
                    <div className='text-xs text-gray-500'>
                      Waiting in queue...
                    </div>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      </CardContent>
    </Card>
  );
}

function CreateVideoForm() {
  const [formData, setFormData] = useState({
    title: '',
    script: '',
    voiceId: '',
    avatarId: '',
    provider: 'D-ID',
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>Create New Video</CardTitle>
        <CardDescription>Generate AI-powered video content</CardDescription>
      </CardHeader>
      <CardContent className='space-y-4'>
        <Input
          placeholder='Video title'
          value={formData.title}
          onChange={e => setFormData({ ...formData, title: e.target.value })}
        />

        <textarea
          className='w-full p-3 border border-gray-300 rounded-md resize-none'
          placeholder='Enter your script here...'
          rows={4}
          value={formData.script}
          onChange={e => setFormData({ ...formData, script: e.target.value })}
        />

        <div className='grid grid-cols-2 gap-4'>
          <div>
            <label className='text-sm font-medium text-gray-700 mb-2 block'>
              Voice
            </label>
            <select
              className='w-full p-2 border border-gray-300 rounded-md'
              value={formData.voiceId}
              onChange={e =>
                setFormData({ ...formData, voiceId: e.target.value })
              }
            >
              <option value=''>Select voice...</option>
              <option value='sarah'>Sarah - Professional</option>
              <option value='marcus'>Marcus - Friendly</option>
              <option value='elena'>Elena - Executive</option>
            </select>
          </div>

          <div>
            <label className='text-sm font-medium text-gray-700 mb-2 block'>
              Avatar
            </label>
            <select
              className='w-full p-2 border border-gray-300 rounded-md'
              value={formData.avatarId}
              onChange={e =>
                setFormData({ ...formData, avatarId: e.target.value })
              }
            >
              <option value=''>Select avatar...</option>
              <option value='business-woman'>Business Woman</option>
              <option value='professional-man'>Professional Man</option>
              <option value='casual-presenter'>Casual Presenter</option>
            </select>
          </div>
        </div>

        <div>
          <label className='text-sm font-medium text-gray-700 mb-2 block'>
            Provider
          </label>
          <div className='flex space-x-4'>
            <label className='flex items-center'>
              <input
                type='radio'
                value='D-ID'
                checked={formData.provider === 'D-ID'}
                onChange={e =>
                  setFormData({ ...formData, provider: e.target.value })
                }
                className='mr-2'
              />
              D-ID
            </label>
            <label className='flex items-center'>
              <input
                type='radio'
                value='HeyGen'
                checked={formData.provider === 'HeyGen'}
                onChange={e =>
                  setFormData({ ...formData, provider: e.target.value })
                }
                className='mr-2'
              />
              HeyGen
            </label>
          </div>
        </div>

        <div className='flex space-x-2 pt-4'>
          <Button className='flex-1'>
            <Video className='h-4 w-4 mr-2' />
            Generate Video
          </Button>
          <Button variant='outline'>
            <Settings className='h-4 w-4' />
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

function VideoGenerationStats() {
  const stats = [
    { label: 'Videos Generated', value: '1,247', icon: Video, color: 'blue' },
    { label: 'Processing Time', value: '2.3 min', icon: Clock, color: 'green' },
    {
      label: 'Success Rate',
      value: '98.5%',
      icon: CheckCircle,
      color: 'green',
    },
    { label: 'Queue Length', value: '5', icon: Loader2, color: 'orange' },
  ];

  const colorClasses = {
    blue: 'text-blue-600 bg-blue-50',
    green: 'text-green-600 bg-green-50',
    orange: 'text-orange-600 bg-orange-50',
  };

  return (
    <div className='grid gap-6 md:grid-cols-2 lg:grid-cols-4'>
      {stats.map(stat => (
        <Card key={stat.label}>
          <CardHeader className='flex flex-row items-center justify-between space-y-0 pb-2'>
            <CardTitle className='text-sm font-medium'>{stat.label}</CardTitle>
            <div
              className={`h-8 w-8 rounded-full flex items-center justify-center ${colorClasses[stat.color as keyof typeof colorClasses]}`}
            >
              <stat.icon className='h-4 w-4' />
            </div>
          </CardHeader>
          <CardContent>
            <div className='text-2xl font-bold'>{stat.value}</div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

export function VideoGenerationStudio() {
  const [activeTab, setActiveTab] = useState<'projects' | 'create' | 'queue'>(
    'projects'
  );

  const mockProjects: VideoProject[] = [
    {
      id: '1',
      title: 'Product Demo Video',
      status: 'completed',
      duration: '2:34',
      createdAt: '2 hours ago',
      thumbnail: '',
      provider: 'D-ID',
    },
    {
      id: '2',
      title: 'Welcome Message',
      status: 'processing',
      duration: '1:45',
      createdAt: '30 min ago',
      thumbnail: '',
      provider: 'HeyGen',
    },
    {
      id: '3',
      title: 'Training Video',
      status: 'draft',
      duration: '5:12',
      createdAt: '1 day ago',
      thumbnail: '',
      provider: 'D-ID',
    },
  ];

  const mockJobs: GenerationJob[] = [
    {
      id: '1',
      title: 'Marketing Explainer',
      status: 'processing',
      progress: 75,
      estimatedTime: '3 min',
      provider: 'D-ID',
    },
    {
      id: '2',
      title: 'Company Update',
      status: 'queued',
      progress: 0,
      estimatedTime: '5 min',
      provider: 'HeyGen',
    },
  ];

  return (
    <div className='space-y-6 p-6'>
      {/* Header */}
      <div className='flex items-center justify-between'>
        <div>
          <h1 className='text-3xl font-bold text-gray-900'>
            Video Generation Studio
          </h1>
          <p className='text-gray-600 mt-2'>
            Create AI-powered videos with D-ID and HeyGen
          </p>
        </div>
        <Button>
          <Upload className='h-4 w-4 mr-2' />
          Upload Assets
        </Button>
      </div>

      {/* Stats */}
      <VideoGenerationStats />

      {/* Navigation Tabs */}
      <div className='border-b border-gray-200'>
        <nav className='-mb-px flex space-x-8'>
          <button
            onClick={() => setActiveTab('projects')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'projects'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Projects
          </button>
          <button
            onClick={() => setActiveTab('create')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'create'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Create New
          </button>
          <button
            onClick={() => setActiveTab('queue')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'queue'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Queue ({mockJobs.length})
          </button>
        </nav>
      </div>

      {/* Tab Content */}
      {activeTab === 'projects' && (
        <div>
          <div className='flex items-center justify-between mb-6'>
            <h2 className='text-xl font-semibold'>Your Projects</h2>
            <div className='flex space-x-2'>
              <Button variant='outline' size='sm'>
                Filter
              </Button>
              <Button variant='outline' size='sm'>
                Sort
              </Button>
            </div>
          </div>

          <div className='grid gap-6 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4'>
            {mockProjects.map(project => (
              <ProjectCard key={project.id} project={project} />
            ))}
          </div>
        </div>
      )}

      {activeTab === 'create' && (
        <div className='max-w-2xl'>
          <CreateVideoForm />
        </div>
      )}

      {activeTab === 'queue' && <GenerationQueue jobs={mockJobs} />}
    </div>
  );
}
