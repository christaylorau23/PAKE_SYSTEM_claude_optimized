# PAKE System Dashboard - Vercel Deployment Guide

## 🚀 Quick Deployment

The PAKE System dashboard is now ready for deployment to Vercel! Here's how to get it live:

### **Option 1: Automated Deployment (Recommended)**

1. **Navigate to the dashboard directory:**
   ```bash
   cd dashboard
   ```

2. **Run the deployment script:**
   ```bash
   ./deploy.sh
   ```

3. **Follow the prompts:**
   - Enter your GitHub Personal Access Token when prompted
   - The script will handle everything else automatically

### **Option 2: Manual Vercel Deployment**

1. **Install Vercel CLI:**
   ```bash
   npm install -g vercel
   ```

2. **Login to Vercel:**
   ```bash
   vercel login
   ```

3. **Deploy from dashboard directory:**
   ```bash
   cd dashboard
   vercel --prod
   ```

4. **Set environment variables:**
   ```bash
   vercel env add GITHUB_TOKEN production
   vercel env add GITHUB_REPO production
   ```

### **Option 3: GitHub Integration**

1. **Connect your GitHub repository to Vercel:**
   - Go to [vercel.com](https://vercel.com)
   - Import your `christaylorau23/PAKE-System` repository
   - Set the root directory to `dashboard`

2. **Configure environment variables in Vercel dashboard:**
   - `GITHUB_TOKEN`: Your GitHub Personal Access Token
   - `GITHUB_REPO`: `christaylorau23/PAKE-System`

## 🔑 Required Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `GITHUB_TOKEN` | GitHub Personal Access Token with `repo` scope | `ghp_xxxxxxxxxxxx` |
| `GITHUB_REPO` | Repository in `owner/repo` format | `christaylorau23/PAKE-System` |

## 📋 GitHub Token Setup

1. **Go to GitHub Settings:**
   - Visit: https://github.com/settings/tokens
   - Click "Generate new token (classic)"

2. **Configure token:**
   - **Note**: "PAKE System Dashboard"
   - **Expiration**: 90 days (or your preference)
   - **Scopes**: Check `repo` (Full control of private repositories)

3. **Copy the token:**
   - Save it securely - you won't see it again!

## 🎯 Dashboard Features

Once deployed, your dashboard will show:

### **Real-time Status Monitoring**
- ✅ GitHub Actions workflow status
- ✅ System health indicators
- ✅ Success rates and metrics
- ✅ Active services count

### **Workflow History**
- 📊 Recent workflow runs (last 20)
- 🔗 Direct links to GitHub Actions
- ⏰ Timestamps and duration
- 🌿 Branch information

### **Auto-refresh**
- 🔄 Updates every 30 seconds
- 📱 Responsive design for all devices
- 🎨 Modern, professional UI

## 🔧 Troubleshooting

### **Common Issues:**

1. **"GitHub token not configured"**
   - Ensure `GITHUB_TOKEN` is set in Vercel environment variables
   - Verify token has `repo` scope

2. **"Failed to fetch system status"**
   - Check GitHub API rate limits
   - Verify repository name is correct

3. **Build failures**
   - Ensure all dependencies are installed
   - Check TypeScript configuration

### **Verification Steps:**

1. **Check deployment:**
   ```bash
   vercel ls
   ```

2. **View logs:**
   ```bash
   vercel logs
   ```

3. **Test locally:**
   ```bash
   cd dashboard
   npm run dev
   ```

## 🌐 Access Your Dashboard

After successful deployment, your dashboard will be available at:
- **Vercel URL**: `https://pake-system-dashboard.vercel.app`
- **Custom Domain**: (if configured in Vercel)

## 📊 What You'll See

The dashboard provides comprehensive visibility into:

- **CI/CD Pipeline Health**: All GitHub Actions workflows
- **System Status**: Overall health and performance metrics
- **Security Monitoring**: Security audit results
- **Deployment History**: Recent releases and changes

## 🎉 Success!

Your PAKE System dashboard is now live and monitoring your enterprise platform in real-time!

**Next Steps:**
1. Bookmark your dashboard URL
2. Share with your team
3. Monitor system health regularly
4. Set up alerts for critical failures

---

**Need Help?** Check the dashboard README.md for detailed documentation and troubleshooting.
