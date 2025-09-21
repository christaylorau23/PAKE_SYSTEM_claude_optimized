# PAKE System Frontend

A transcendent web application built with Next.js, featuring quantum-level responsiveness and cognitive ergonomics.

## Context7 API Integration

This project integrates with Context7 API for enhanced search and development workflows.

### Context7 API Usage

```bash
# Search for development resources
curl -X GET "https://context7.com/api/v1/search?query=react+hook+form" \
  -H "Authorization: Bearer ctx7sk-cd355449-4329-4692-b3f8-981a68ec56fe"

# Example searches for common development tasks
curl -X GET "https://context7.com/api/v1/search?query=next.js+vercel+deployment" \
  -H "Authorization: Bearer ctx7sk-cd355449-4329-4692-b3f8-981a68ec56fe"

curl -X GET "https://context7.com/api/v1/search?query=supabase+integration" \
  -H "Authorization: Bearer ctx7sk-cd355449-4329-4692-b3f8-981a68ec56fe"
```

### Development Workflow with Context7

All Claude Code actions now utilize Context7 API for:

- Component research and implementation guidance
- Best practices lookup
- Troubleshooting deployment issues
- Framework-specific solutions

## Supabase Integration

This project includes Supabase integration for:

- User authentication and session management
- Real-time database capabilities
- Edge-optimized API endpoints
- Automatic Vercel deployment integration

### Supabase Setup

1. **Create a Supabase Project**: Go to [supabase.com](https://supabase.com) and create a new project
2. **Get your credentials**: Copy your project URL and anon key from Settings > API
3. **Set environment variables**:

```bash
# Copy the example file
cp .env.local.example .env.local

# Add your Supabase credentials
NEXT_PUBLIC_SUPABASE_URL=your_supabase_project_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
```

4. **Install Supabase integration on Vercel**:
   - Go to [Vercel Marketplace](https://vercel.com/marketplace/supabase)
   - Install the Supabase integration
   - This automatically configures environment variables and preview deployments

## Getting Started

First, install dependencies and set up environment variables:

```bash
npm install
cp .env.local.example .env.local
# Edit .env.local with your Supabase credentials
```

Then run the development server:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

You can start editing the page by modifying `app/page.tsx`. The page auto-updates as you edit the file.

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.

## Deployment Troubleshooting

### Common Vercel Deployment Issues

If you encounter **NOT_FOUND (404)** errors after deployment:

1. **Check Framework Preset**:
   - Go to Vercel > Project Settings > Build and Deployment Tab
   - Ensure "Framework Preset" is set to "Next.js" (not "Other")

2. **Verify Build Configuration**:
   - Ensure `next.config.js` is minimal and doesn't contain complex webpack customizations
   - Check that `package.json` build scripts are correct
   - Remove any conflicting `vercel.json` build configurations

3. **Case Sensitivity Issues**:
   - Ensure file names match exactly between local development and git commits
   - Check component imports for correct capitalization

4. **Module Resolution**:
   - Ensure `node_modules` is not committed to git
   - Check that all dependencies are listed in `package.json`
   - Verify all imports use correct relative/absolute paths

### Context7 Integration for Debugging

Use Context7 API to research specific issues:

```bash
# Research deployment problems
curl -X GET "https://context7.com/api/v1/search?query=your-specific-error" \
  -H "Authorization: Bearer ctx7sk-cd355449-4329-4692-b3f8-981a68ec56fe"
```

### Successful Deployment Checklist

- [ ] Framework preset set to "Next.js" in Vercel
- [ ] Minimal `next.config.js` without complex webpack config
- [ ] Supabase integration installed via Vercel Marketplace
- [ ] Environment variables configured in Vercel
- [ ] No `node_modules` in git repository
- [ ] All file names properly capitalized and match imports
- [ ] Build succeeds locally with `npm run build`
