# PAKE System Dashboard

A modern, real-time dashboard for monitoring the PAKE System enterprise knowledge management platform.

## Features

- **Real-time Status Monitoring**: Live updates of GitHub Actions workflows
- **System Health Overview**: Comprehensive health indicators and metrics
- **Workflow History**: Recent workflow runs with detailed status information
- **Responsive Design**: Works on desktop, tablet, and mobile devices
- **Auto-refresh**: Updates every 30 seconds automatically

## Tech Stack

- **Next.js 14**: React framework with App Router
- **TypeScript**: Type-safe development
- **Tailwind CSS**: Utility-first CSS framework
- **Lucide React**: Beautiful, customizable icons
- **GitHub API**: Real-time workflow data

## Getting Started

### Prerequisites

- Node.js 18+ 
- npm or yarn
- GitHub Personal Access Token with `repo` scope

### Installation

1. Install dependencies:
```bash
npm install
```

2. Set up environment variables:
```bash
cp .env.example .env.local
```

Add your GitHub token:
```
GITHUB_TOKEN=your_github_token_here
GITHUB_REPO=christaylorau23/PAKE-System
```

3. Run the development server:
```bash
npm run dev
```

4. Open [http://localhost:3000](http://localhost:3000) in your browser.

## Deployment

### Vercel (Recommended)

1. Install Vercel CLI:
```bash
npm i -g vercel
```

2. Deploy:
```bash
vercel
```

3. Set environment variables in Vercel dashboard:
   - `GITHUB_TOKEN`: Your GitHub personal access token
   - `GITHUB_REPO`: Repository in format `owner/repo`

### Manual Deployment

1. Build the application:
```bash
npm run build
```

2. Start the production server:
```bash
npm start
```

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `GITHUB_TOKEN` | GitHub Personal Access Token with `repo` scope | Yes |
| `GITHUB_REPO` | GitHub repository in `owner/repo` format | No (defaults to christaylorau23/PAKE-System) |

## API Endpoints

- `GET /api/status` - Returns system status and workflow information

## Dashboard Components

### Status Overview
- Total workflow runs
- Success rate percentage
- Active services count
- Security status

### Recent Workflows
- Last 10 workflow runs
- Status indicators (success, failure, in progress)
- Branch information
- Time stamps
- Direct links to GitHub Actions

## Security

- Environment variables are kept secure
- GitHub token is only used server-side
- HTTPS enforced in production
- Security headers configured

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is part of the PAKE System enterprise platform.
