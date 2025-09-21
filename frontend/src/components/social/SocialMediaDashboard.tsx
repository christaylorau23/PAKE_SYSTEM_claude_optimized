'use client';

import { useState } from 'react';
import {
  Calendar,
  BarChart3,
  Users,
  Heart,
  MessageCircle,
  Share2,
  TrendingUp,
  Plus,
  Edit,
  Eye,
  Clock,
  CheckCircle,
  AlertCircle,
  Pause,
  Play,
  Target,
  Zap,
} from 'lucide-react';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Button } from '@/components/ui/button';

interface SocialPost {
  id: string;
  content: string;
  platforms: string[];
  status: 'draft' | 'scheduled' | 'published' | 'failed';
  scheduledTime?: string;
  publishedTime?: string;
  engagement?: {
    likes: number;
    comments: number;
    shares: number;
    reach: number;
  };
  aiGenerated: boolean;
}

interface Campaign {
  id: string;
  name: string;
  status: 'active' | 'paused' | 'completed';
  posts: number;
  engagement: number;
  reach: number;
  startDate: string;
  endDate: string;
  platforms: string[];
}

function SocialMetricsCard({
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
    pink: 'text-pink-600 bg-pink-50',
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

function PostCard({ post }: { post: SocialPost }) {
  const statusStyles = {
    draft: { bg: 'bg-gray-100', text: 'text-gray-800', icon: Edit },
    scheduled: { bg: 'bg-blue-100', text: 'text-blue-800', icon: Clock },
    published: {
      bg: 'bg-green-100',
      text: 'text-green-800',
      icon: CheckCircle,
    },
    failed: { bg: 'bg-red-100', text: 'text-red-800', icon: AlertCircle },
  };

  const style = statusStyles[post.status];
  const StatusIcon = style.icon;

  const platformIcons = {
    Twitter: '🐦',
    LinkedIn: '💼',
    Instagram: '📷',
    Facebook: '📘',
  };

  return (
    <Card className='hover:shadow-md transition-shadow'>
      <CardHeader className='pb-3'>
        <div className='flex items-start justify-between'>
          <div className='flex-1'>
            <div className='flex items-center space-x-2 mb-2'>
              <div
                className={`px-2 py-1 rounded-full text-xs font-medium ${style.bg} ${style.text}`}
              >
                <StatusIcon className='h-3 w-3 inline mr-1' />
                {post.status}
              </div>
              {post.aiGenerated && (
                <div className='px-2 py-1 bg-purple-100 text-purple-800 rounded-full text-xs font-medium'>
                  <Zap className='h-3 w-3 inline mr-1' />
                  AI
                </div>
              )}
            </div>

            <div className='flex space-x-1 mb-2'>
              {post.platforms.map(platform => (
                <span key={platform} className='text-sm'>
                  {platformIcons[platform as keyof typeof platformIcons]}
                </span>
              ))}
            </div>
          </div>

          <div className='flex space-x-1'>
            <Button variant='ghost' size='sm'>
              <Eye className='h-3 w-3' />
            </Button>
            <Button variant='ghost' size='sm'>
              <Edit className='h-3 w-3' />
            </Button>
          </div>
        </div>
      </CardHeader>

      <CardContent className='pt-0'>
        <p className='text-sm text-gray-700 mb-3 line-clamp-3'>
          {post.content}
        </p>

        {post.engagement && (
          <div className='flex items-center justify-between text-xs text-gray-500 bg-gray-50 rounded-lg p-2'>
            <div className='flex items-center space-x-3'>
              <span className='flex items-center'>
                <Heart className='h-3 w-3 mr-1' />
                {post.engagement.likes}
              </span>
              <span className='flex items-center'>
                <MessageCircle className='h-3 w-3 mr-1' />
                {post.engagement.comments}
              </span>
              <span className='flex items-center'>
                <Share2 className='h-3 w-3 mr-1' />
                {post.engagement.shares}
              </span>
            </div>
            <span>Reach: {post.engagement.reach.toLocaleString()}</span>
          </div>
        )}

        {post.scheduledTime && (
          <div className='flex items-center text-xs text-gray-500 mt-2'>
            <Clock className='h-3 w-3 mr-1' />
            Scheduled: {post.scheduledTime}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function CampaignCard({ campaign }: { campaign: Campaign }) {
  const statusColors = {
    active: 'bg-green-100 text-green-800',
    paused: 'bg-yellow-100 text-yellow-800',
    completed: 'bg-gray-100 text-gray-800',
  };

  return (
    <Card className='hover:shadow-md transition-shadow'>
      <CardHeader className='pb-3'>
        <div className='flex items-start justify-between'>
          <div>
            <CardTitle className='text-lg'>{campaign.name}</CardTitle>
            <div
              className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium mt-2 ${statusColors[campaign.status]}`}
            >
              {campaign.status === 'active' && (
                <Play className='h-3 w-3 mr-1' />
              )}
              {campaign.status === 'paused' && (
                <Pause className='h-3 w-3 mr-1' />
              )}
              {campaign.status === 'completed' && (
                <CheckCircle className='h-3 w-3 mr-1' />
              )}
              {campaign.status.charAt(0).toUpperCase() +
                campaign.status.slice(1)}
            </div>
          </div>

          <Button variant='ghost' size='sm'>
            <Edit className='h-4 w-4' />
          </Button>
        </div>
      </CardHeader>

      <CardContent>
        <div className='grid grid-cols-3 gap-4 mb-4'>
          <div className='text-center'>
            <div className='text-2xl font-bold text-blue-600'>
              {campaign.posts}
            </div>
            <div className='text-xs text-gray-500'>Posts</div>
          </div>
          <div className='text-center'>
            <div className='text-2xl font-bold text-green-600'>
              {campaign.engagement}%
            </div>
            <div className='text-xs text-gray-500'>Engagement</div>
          </div>
          <div className='text-center'>
            <div className='text-2xl font-bold text-purple-600'>
              {campaign.reach}K
            </div>
            <div className='text-xs text-gray-500'>Reach</div>
          </div>
        </div>

        <div className='text-xs text-gray-500'>
          {campaign.startDate} - {campaign.endDate}
        </div>

        <div className='flex space-x-1 mt-2'>
          {campaign.platforms.map(platform => (
            <span
              key={platform}
              className='px-2 py-1 bg-gray-100 text-gray-700 rounded text-xs'
            >
              {platform}
            </span>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function ContentCalendar() {
  const scheduledPosts = [
    {
      time: '09:00',
      content: 'Product launch announcement',
      platform: 'Twitter',
    },
    {
      time: '12:00',
      content: 'Behind-the-scenes video',
      platform: 'Instagram',
    },
    {
      time: '15:00',
      content: 'Industry insights article',
      platform: 'LinkedIn',
    },
    {
      time: '18:00',
      content: 'Community engagement post',
      platform: 'Facebook',
    },
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle>Today's Schedule</CardTitle>
        <CardDescription>
          Upcoming posts for {new Date().toLocaleDateString()}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className='space-y-4'>
          {scheduledPosts.map((post, index) => (
            <div
              key={index}
              className='flex items-center space-x-3 p-3 border border-gray-100 rounded-lg'
            >
              <div className='text-sm font-mono font-medium text-gray-600 w-16'>
                {post.time}
              </div>
              <div className='flex-1'>
                <div className='text-sm font-medium'>{post.content}</div>
                <div className='text-xs text-gray-500'>{post.platform}</div>
              </div>
              <Button variant='ghost' size='sm'>
                <Edit className='h-3 w-3' />
              </Button>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function AIContentGenerator() {
  const [prompt, setPrompt] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);

  const handleGenerate = () => {
    setIsGenerating(true);
    // Simulate API call
    setTimeout(() => {
      setIsGenerating(false);
    }, 2000);
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>AI Content Generator</CardTitle>
        <CardDescription>
          Generate engaging social media content with AI
        </CardDescription>
      </CardHeader>
      <CardContent className='space-y-4'>
        <textarea
          className='w-full p-3 border border-gray-300 rounded-md resize-none'
          placeholder='Describe what you want to post about...'
          rows={3}
          value={prompt}
          onChange={e => setPrompt(e.target.value)}
        />

        <div className='flex items-center space-x-2'>
          <Button
            onClick={handleGenerate}
            disabled={!prompt.trim() || isGenerating}
            className='flex-1'
          >
            {isGenerating ? (
              <>
                <div className='animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2' />
                Generating...
              </>
            ) : (
              <>
                <Zap className='h-4 w-4 mr-2' />
                Generate Content
              </>
            )}
          </Button>

          <Button variant='outline'>
            <Target className='h-4 w-4' />
          </Button>
        </div>

        <div className='flex flex-wrap gap-2'>
          {[
            'Product Launch',
            'Industry News',
            'Company Update',
            'Engagement',
            'Educational',
          ].map(template => (
            <button
              key={template}
              className='px-3 py-1 bg-gray-100 text-gray-700 rounded-full text-xs hover:bg-gray-200 transition-colors'
              onClick={() =>
                setPrompt(`Create a ${template.toLowerCase()} post about `)
              }
            >
              {template}
            </button>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

export function SocialMediaDashboard() {
  const [activeTab, setActiveTab] = useState<
    'overview' | 'posts' | 'campaigns' | 'calendar'
  >('overview');

  const mockPosts: SocialPost[] = [
    {
      id: '1',
      content:
        'Excited to announce our latest product feature! 🚀 This game-changing update will revolutionize how you manage your workflow.',
      platforms: ['Twitter', 'LinkedIn'],
      status: 'published',
      publishedTime: '2 hours ago',
      engagement: { likes: 45, comments: 12, shares: 8, reach: 2341 },
      aiGenerated: true,
    },
    {
      id: '2',
      content:
        'Behind the scenes at our office today. Our team is working hard to bring you the best experience possible! #TeamWork',
      platforms: ['Instagram', 'Facebook'],
      status: 'scheduled',
      scheduledTime: 'Today 3:00 PM',
      aiGenerated: false,
    },
    {
      id: '3',
      content:
        'Industry insights: The future of AI in business automation. What trends are you seeing in your organization?',
      platforms: ['LinkedIn'],
      status: 'draft',
      aiGenerated: true,
    },
  ];

  const mockCampaigns: Campaign[] = [
    {
      id: '1',
      name: 'Q4 Product Launch',
      status: 'active',
      posts: 24,
      engagement: 8.7,
      reach: 45,
      startDate: 'Oct 1',
      endDate: 'Dec 31',
      platforms: ['Twitter', 'LinkedIn', 'Facebook'],
    },
    {
      id: '2',
      name: 'Brand Awareness',
      status: 'paused',
      posts: 12,
      engagement: 6.2,
      reach: 23,
      startDate: 'Sep 15',
      endDate: 'Nov 30',
      platforms: ['Instagram', 'Facebook'],
    },
  ];

  return (
    <div className='space-y-6 p-6'>
      {/* Header */}
      <div className='flex items-center justify-between'>
        <div>
          <h1 className='text-3xl font-bold text-gray-900'>
            Social Media Dashboard
          </h1>
          <p className='text-gray-600 mt-2'>
            Manage your social media presence across all platforms
          </p>
        </div>
        <div className='flex space-x-2'>
          <Button variant='outline'>
            <Calendar className='h-4 w-4 mr-2' />
            Schedule
          </Button>
          <Button>
            <Plus className='h-4 w-4 mr-2' />
            Create Post
          </Button>
        </div>
      </div>

      {/* Metrics */}
      <div className='grid gap-6 md:grid-cols-2 lg:grid-cols-5'>
        <SocialMetricsCard
          title='Total Reach'
          value='127K'
          icon={Users}
          trend='↑ 12% this week'
          color='blue'
        />
        <SocialMetricsCard
          title='Engagement Rate'
          value='8.7%'
          icon={Heart}
          trend='↑ 2.3% vs last week'
          color='pink'
        />
        <SocialMetricsCard
          title='Posts Published'
          value='45'
          icon={Share2}
          trend='This month'
          color='green'
        />
        <SocialMetricsCard
          title='Growth Rate'
          value='15.3%'
          icon={TrendingUp}
          trend='Month over month'
          color='purple'
        />
        <SocialMetricsCard
          title='AI Generated'
          value='67%'
          icon={Zap}
          trend='Of total content'
          color='orange'
        />
      </div>

      {/* Navigation Tabs */}
      <div className='border-b border-gray-200'>
        <nav className='-mb-px flex space-x-8'>
          {[
            { key: 'overview', label: 'Overview' },
            { key: 'posts', label: 'Posts' },
            { key: 'campaigns', label: 'Campaigns' },
            { key: 'calendar', label: 'Calendar' },
          ].map(tab => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key as any)}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                activeTab === tab.key
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      {activeTab === 'overview' && (
        <div className='grid gap-6 lg:grid-cols-3'>
          <div className='lg:col-span-2'>
            <ContentCalendar />
          </div>
          <AIContentGenerator />
        </div>
      )}

      {activeTab === 'posts' && (
        <div>
          <div className='flex items-center justify-between mb-6'>
            <h2 className='text-xl font-semibold'>Recent Posts</h2>
            <div className='flex space-x-2'>
              <Button variant='outline' size='sm'>
                Filter
              </Button>
              <Button variant='outline' size='sm'>
                Sort
              </Button>
            </div>
          </div>

          <div className='grid gap-6 md:grid-cols-2 lg:grid-cols-3'>
            {mockPosts.map(post => (
              <PostCard key={post.id} post={post} />
            ))}
          </div>
        </div>
      )}

      {activeTab === 'campaigns' && (
        <div>
          <div className='flex items-center justify-between mb-6'>
            <h2 className='text-xl font-semibold'>Active Campaigns</h2>
            <Button>
              <Plus className='h-4 w-4 mr-2' />
              New Campaign
            </Button>
          </div>

          <div className='grid gap-6 md:grid-cols-2 lg:grid-cols-3'>
            {mockCampaigns.map(campaign => (
              <CampaignCard key={campaign.id} campaign={campaign} />
            ))}
          </div>
        </div>
      )}

      {activeTab === 'calendar' && (
        <div className='max-w-4xl'>
          <ContentCalendar />
        </div>
      )}
    </div>
  );
}
