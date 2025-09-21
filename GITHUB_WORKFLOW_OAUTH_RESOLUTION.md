# GitHub Workflow OAuth Scope Resolution

## Issue Summary

The GitHub workflow files have been updated to resolve OAuth scope requirements, but the current OAuth app doesn't have the `workflow` scope needed to push workflow files to GitHub.

## Root Cause

The OAuth app being used for GitHub authentication lacks the `workflow` scope, which is required to create or update workflow files in the `.github/workflows/` directory.

## Solution Options

### Option 1: Manual GitHub Web Interface (Recommended)

1. **Navigate to GitHub Repository**: Go to https://github.com/christaylorau23/PAKE-System
2. **Access Workflow Files**: Navigate to `.github/workflows/` directory
3. **Update Each Workflow File**: Copy the updated content from the local files and paste into GitHub web interface
4. **Commit Changes**: Use GitHub's web interface to commit the changes

### Option 2: Personal Access Token with Workflow Scope

1. **Create Personal Access Token**:
   - Go to GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)
   - Generate new token with `workflow` scope
   - Copy the token

2. **Update Git Remote**:
   ```bash
   git remote set-url origin https://<token>@github.com/christaylorau23/PAKE-System.git
   ```

3. **Push Changes**:
   ```bash
   git add .github/workflows/
   git commit -m "fix: Resolve GitHub workflow OAuth scope requirements"
   git push origin main
   ```

### Option 3: GitHub CLI Authentication

1. **Install GitHub CLI** (if not already installed):
   ```bash
   curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
   echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
   sudo apt update
   sudo apt install gh
   ```

2. **Authenticate with GitHub CLI**:
   ```bash
   gh auth login
   ```

3. **Push Changes**:
   ```bash
   git add .github/workflows/
   git commit -m "fix: Resolve GitHub workflow OAuth scope requirements"
   git push origin main
   ```

## Workflow Files Updated

The following workflow files have been updated with proper OAuth permissions:

1. **`.github/workflows/ci.yml`**
   - Added explicit permissions block
   - Updated to use modern GitHub Actions

2. **`.github/workflows/release.yml`**
   - Added explicit permissions block
   - Replaced deprecated `actions/create-release@v1` with GitHub CLI
   - Replaced deprecated `actions/upload-release-asset@v1` with `gh release upload`

3. **`.github/workflows/secrets-detection.yml`**
   - Added explicit permissions block
   - Updated to use official `trufflesecurity/trufflehog@main` action

4. **`.github/workflows/security-audit.yml`**
   - Already had proper permissions block
   - No changes needed

5. **`.github/workflows/security.yml`**
   - Added explicit permissions block

6. **`.github/workflows/debug-node.yml`**
   - Added explicit permissions block

7. **`.github/workflows/ml-pipeline.yml`**
   - Added explicit permissions block

## Standard Permissions Applied

All workflows now include appropriate permissions:

```yaml
permissions:
  contents: read          # Read repository contents
  security-events: write  # Write security events
  issues: write          # Write issues
  pull-requests: write  # Write pull requests
  actions: read          # Read actions
  checks: read           # Read checks
  packages: read/write   # Read/write packages (as needed)
```

## Verification

After applying the solution:

1. **Check Workflow Status**: Verify workflows run successfully in GitHub Actions
2. **Test Permissions**: Ensure all workflow steps have necessary permissions
3. **Monitor Security**: Verify security scans and secrets detection work properly

## Next Steps

1. Choose and implement one of the solution options above
2. Verify all workflows are functioning correctly
3. Remove this resolution document once the issue is resolved

## Files Ready for Commit

The following files are ready to be committed once the OAuth scope issue is resolved:

- `.github/workflows/ci.yml`
- `.github/workflows/debug-node.yml`
- `.github/workflows/ml-pipeline.yml`
- `.github/workflows/release.yml`
- `.github/workflows/secrets-detection.yml`
- `.github/workflows/security-audit.yml`
- `.github/workflows/security.yml`

All files have been updated with proper OAuth permissions and modern GitHub Actions practices.
