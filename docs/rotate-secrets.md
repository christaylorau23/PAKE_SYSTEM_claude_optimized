# 🔐 EMERGENCY SECRET ROTATION GUIDE

**SECURITY BREACH RESPONSE - EXECUTE IMMEDIATELY**

⚠️ **CRITICAL**: All secrets in this repository have been exposed in version control and must be rotated immediately.

## 📋 ROTATION CHECKLIST

### Phase 1: Immediate Actions (Execute Now)
- [ ] **Stop all running services** to prevent unauthorized access
- [ ] **Generate new strong REDACTED_SECRETs** for all services  
- [ ] **Rotate database credentials**
- [ ] **Invalidate and regenerate API keys**
- [ ] **Update service configurations**
- [ ] **Restart services with new credentials**

### Phase 2: Git History Cleanup
- [ ] **Purge secrets from git history** using git-filter-repo
- [ ] **Verify complete removal** of sensitive data
- [ ] **Force push cleaned repository**

### Phase 3: Long-term Security
- [ ] **Implement proper secret management**
- [ ] **Set up monitoring and alerts**
- [ ] **Document incident for future prevention**

---

## 🚨 STEP-BY-STEP ROTATION COMMANDS

### **STEP 1: Stop All Services**
```bash
# Stop Docker services
cd D:\Projects\PAKE_SYSTEM\docker
docker-compose down

# Stop any manual processes
pkill -f "python.*mcp"
pkill -f "node.*bridge"
```

### **STEP 2: Generate New Strong Passwords**

**Generate 16-character REDACTED_SECRETs for each service:**
```powershell
# PowerShell REDACTED_SECRET generation
-join ((33..126) | Get-Random -Count 16 | % {[char]$_})
-join ((33..126) | Get-Random -Count 16 | % {[char]$_})  
-join ((33..126) | Get-Random -Count 16 | % {[char]$_})
-join ((33..126) | Get-Random -Count 16 | % {[char]$_})
```

**Or using Python:**
```bash
python -c "import secrets, string; chars=string.ascii_letters+string.digits+'!@#$%^&*'; print(''.join(secrets.choice(chars) for _ in range(16)))"
```

**Record new REDACTED_SECRETs:**
- NEW_POSTGRES_PASSWORD: `________________________`
- NEW_REDIS_PASSWORD: `________________________`  
- NEW_N8N_PASSWORD: `________________________`
- NEW_DB_PASSWORD: `________________________`

### **STEP 3: Update Environment Files**

**Create secure .env file:**
```bash
cd D:\Projects\PAKE_SYSTEM

# Backup existing .env (for reference)
mv .env .env.compromised.backup

# Create new .env from template
cp .env.example .env

# Edit with new REDACTED_SECRETs (use your preferred editor)
notepad .env
# OR
nano .env
```

**Update the following values in .env:**
```bash
DB_PASSWORD=YOUR_NEW_POSTGRES_PASSWORD_HERE
POSTGRES_PASSWORD=YOUR_NEW_POSTGRES_PASSWORD_HERE
REDIS_PASSWORD=YOUR_NEW_REDIS_PASSWORD_HERE
N8N_PASSWORD=YOUR_NEW_N8N_PASSWORD_HERE
```

**Update docker/.env file:**
```bash
cd docker
mv .env .env.compromised.backup
```

**Create new docker/.env:**
```bash
cat > .env << 'EOF'
# PAKE+ System Environment Variables - ROTATED $(date +%Y-%m-%d)

# Database Configuration  
POSTGRES_PASSWORD=YOUR_NEW_POSTGRES_PASSWORD_HERE
POSTGRES_PORT=5432

# Redis Configuration
REDIS_PASSWORD=YOUR_NEW_REDIS_PASSWORD_HERE
REDIS_PORT=6379

# MCP Server Configuration
MCP_PORT=8000
OPENAI_API_KEY=your_new_openai_key_here

# n8n Configuration
N8N_USER=admin
N8N_PASSWORD=YOUR_NEW_N8N_PASSWORD_HERE
N8N_HOST=localhost
N8N_PORT=5678

# Nginx Configuration
NGINX_PORT=80
NGINX_HTTPS_PORT=443

# Ollama Configuration  
OLLAMA_PORT=11434

# External API Keys - ROTATE IMMEDIATELY
ELEVENLABS_API_KEY=your_new_elevenlabs_key_here
ANTHROPIC_API_KEY=your_new_anthropic_key_here
EOF
```

### **STEP 4: Rotate External API Keys**

**OpenAI API Key:**
```bash
# 1. Go to https://platform.openai.com/api-keys
# 2. Delete the exposed key: [EXPOSED_KEY_ID]
# 3. Create new key with minimal required permissions
# 4. Update .env with new key: OPENAI_API_KEY=sk-new_key_here
```

**Anthropic API Key:**
```bash
# 1. Go to https://console.anthropic.com/account/keys
# 2. Revoke exposed key immediately
# 3. Generate new key with restricted scope
# 4. Update .env with new key: ANTHROPIC_API_KEY=new_key_here
```

**ElevenLabs API Key:**
```bash  
# 1. Go to https://elevenlabs.io/api-keys
# 2. Delete compromised key
# 3. Create new key with minimal permissions
# 4. Update .env: ELEVENLABS_API_KEY=new_key_here
```

**Other API Keys (if configured):**
- YouTube API Key: https://console.developers.google.com/apis/credentials
- LinkedIn API Key: https://www.linkedin.com/developers/apps
- Twitter API Key: https://developer.twitter.com/en/portal/dashboard

### **STEP 5: Update Database Configurations**

**Reset PostgreSQL REDACTED_SECRET:**
```bash
cd D:\Projects\PAKE_SYSTEM\docker

# Start only PostgreSQL to reset REDACTED_SECRET
docker-compose up -d postgres

# Wait 10 seconds for startup
timeout 10

# Reset REDACTED_SECRET
docker-compose exec postgres psql -U postgres -c "ALTER USER pake_user PASSWORD 'YOUR_NEW_DB_PASSWORD_HERE';"

# Stop PostgreSQL
docker-compose down
```

**Reset Redis REDACTED_SECRET:**
```bash
# Redis REDACTED_SECRET will be updated when services restart with new config
# No manual reset needed - handled by docker-compose restart
```

### **STEP 6: Restart All Services**

**Start services with new credentials:**
```bash
cd D:\Projects\PAKE_SYSTEM\docker

# Start all services
docker-compose up -d

# Verify all services are healthy
docker-compose ps

# Check logs for any credential errors  
docker-compose logs postgres | head -20
docker-compose logs redis | head -20
docker-compose logs n8n | head -20
```

**Test service connectivity:**
```bash
# Test PostgreSQL connection
docker-compose exec postgres psql -U pake_user -d pake_system -c "SELECT version();"

# Test Redis connection  
docker-compose exec redis redis-cli -a YOUR_NEW_REDIS_PASSWORD_HERE ping

# Test n8n login at http://localhost:5678
# Username: admin
# Password: YOUR_NEW_N8N_PASSWORD_HERE
```

### **STEP 7: Update Application Configurations**

**Update any hardcoded configs in source files:**
```bash
# Search for old REDACTED_SECRETs in source code
cd D:\Projects\PAKE_SYSTEM
grep -r "process.env.SERVICE_PASSWORD || 'SECURE_PASSWORD_REQUIRED'" . --exclude-dir=.git
grep -r "process.env.REDIS_PASSWORD || 'SECURE_PASSWORD_REQUIRED'" . --exclude-dir=.git  
grep -r "n8n_secure_2024" . --exclude-dir=.git

# Replace any found instances with environment variable references
```

**Restart application services:**
```bash
# If running Python MCP servers
cd mcp-servers  
# Stop existing processes first
pkill -f "python.*base_server"

# Start with new environment
python base_server.py

# If running Node.js bridge
cd scripts
node obsidian_bridge.js
```

---

## 🧹 GIT HISTORY CLEANUP

### **STEP 8: Install git-filter-repo**

**Windows installation:**
```bash
# Using pip
pip install git-filter-repo

# OR using conda
conda install -c conda-forge git-filter-repo

# OR manual installation
curl -o git-filter-repo https://raw.githubusercontent.com/newren/git-filter-repo/main/git-filter-repo
chmod +x git-filter-repo
mv git-filter-repo /usr/local/bin/
```

### **STEP 9: Purge Secrets from Git History**

**⚠️ WARNING: Create backup before running these commands**

```bash
cd D:\Projects\PAKE_SYSTEM

# Create backup
git bundle create ../PAKE_SYSTEM-backup.bundle --all

# Purge all .env files from history
git filter-repo --path .env --invert-paths

# Purge docker/.env files  
git filter-repo --path docker/.env --invert-paths

# Purge any other environment files
git filter-repo --path scripts/.env --invert-paths
git filter-repo --path configs/.env --invert-paths

# Remove specific exposed secrets from all files
git filter-repo --replace-text ../secrets-to-remove.txt
```

**Create secrets-to-remove.txt:**
```bash
cat > ../secrets-to-remove.txt << 'EOF'
process.env.SERVICE_PASSWORD || 'SECURE_PASSWORD_REQUIRED'=***REMOVED***
process.env.REDIS_PASSWORD || 'SECURE_PASSWORD_REQUIRED'=***REMOVED***  
n8n_secure_2024=***REMOVED***
your_REDACTED_SECRET_here=***REMOVED***
your_openai_key_here=***REMOVED***
your_elevenlabs_key_here=***REMOVED***
your_anthropic_key_here=***REMOVED***
EOF
```

### **STEP 10: Verify Complete Removal**

**Search for any remaining secrets:**
```bash
# Check git history for exposed secrets
git log --all --full-history --source -- .env
git log --all --full-history --source -- docker/.env

# Search all history for secret strings
git log --all -S "process.env.SERVICE_PASSWORD || 'SECURE_PASSWORD_REQUIRED'" --source --patch
git log --all -S "process.env.REDIS_PASSWORD || 'SECURE_PASSWORD_REQUIRED'" --source --patch
git log --all -S "n8n_secure_2024" --source --patch

# Verify no secrets remain
git grep -i "pake_secure\|redis_secure\|n8n_secure" $(git rev-list --all)
```

**If any secrets found, repeat filtering:**
```bash
# Remove specific commits containing secrets
git filter-repo --commit-callback '
  if b"process.env.SERVICE_PASSWORD || 'SECURE_PASSWORD_REQUIRED'" in commit.message or b"process.env.REDIS_PASSWORD || 'SECURE_PASSWORD_REQUIRED'" in commit.message:
    commit.message = b"***SANITIZED COMMIT MESSAGE***"
'
```

### **STEP 11: Force Push Cleaned Repository**

**⚠️ CRITICAL: This overwrites remote history**

```bash
# Add new .env.example and .gitignore
git add .env.example .gitignore README.md rotate-secrets.md
git commit -m "security: implement secure environment configuration

- Add comprehensive .env.example template
- Update .gitignore to block all secret files  
- Document secret rotation procedures
- Remove exposed credentials from codebase

SECURITY: All previous credentials have been rotated"

# Force push cleaned history
git push origin --force --all
git push origin --force --tags
```

---

## 📊 VERIFICATION CHECKLIST

### **Post-Rotation Verification**

- [ ] **All services start successfully** with new credentials
- [ ] **Database connections work** with new REDACTED_SECRETs  
- [ ] **API endpoints respond** correctly
- [ ] **No old REDACTED_SECRETs** found in git history
- [ ] **All team members notified** of new credentials
- [ ] **Documentation updated** with rotation date

### **Test Commands**

```bash
# Verify service health
curl http://localhost:8000/health
curl http://localhost:3000/health
curl http://localhost:5678/healthz

# Test database connectivity
docker-compose exec postgres pg_isready -U pake_user

# Verify Redis authentication
docker-compose exec redis redis-cli -a YOUR_NEW_REDIS_PASSWORD_HERE ping

# Check git history is clean
git log --oneline | head -10
git log --all -S "process.env.SERVICE_PASSWORD || 'SECURE_PASSWORD_REQUIRED'" --oneline
```

---

## 🛡️ LONG-TERM SECURITY MEASURES

### **Implement Secret Management**

**Option 1: AWS Secrets Manager**
```bash
# Store secrets in AWS Secrets Manager
aws secretsmanager create-secret --name "pake-system/database" \
  --secret-string '{"REDACTED_SECRET":"YOUR_NEW_DB_PASSWORD_HERE"}'

aws secretsmanager create-secret --name "pake-system/redis" \
  --secret-string '{"REDACTED_SECRET":"YOUR_NEW_REDIS_PASSWORD_HERE"}'
```

**Option 2: HashiCorp Vault**
```bash
# Store in Vault
vault kv put secret/pake-system/database REDACTED_SECRET="YOUR_NEW_DB_PASSWORD_HERE"
vault kv put secret/pake-system/redis REDACTED_SECRET="YOUR_NEW_REDIS_PASSWORD_HERE"
```

**Option 3: Azure Key Vault**
```bash
# Store in Azure Key Vault  
az keyvault secret set --vault-name "pake-keyvault" --name "db-REDACTED_SECRET" --value "YOUR_NEW_DB_PASSWORD_HERE"
az keyvault secret set --vault-name "pake-keyvault" --name "redis-REDACTED_SECRET" --value "YOUR_NEW_REDIS_PASSWORD_HERE"
```

### **Set Up Monitoring**

```bash
# Monitor for secret exposure
git config --global commit.template .gitmessage
git config --global pre-commit.enabled true

# Set up alerts for .env files
echo "*.env" >> .git/hooks/pre-commit-secrets-check
```

### **Regular Rotation Schedule**

- [ ] **Set calendar reminder** for quarterly secret rotation
- [ ] **Document all rotated credentials** in secure REDACTED_SECRET manager
- [ ] **Review access logs** monthly for suspicious activity  
- [ ] **Audit permissions** on all external API keys
- [ ] **Update incident response plan** based on lessons learned

---

## 📝 INCIDENT DOCUMENTATION

**Date of Secret Exposure Discovery:** `_________________`

**Date of Rotation Completion:** `_________________`

**Exposed Secrets:**
- [x] PostgreSQL database REDACTED_SECRET (`process.env.SERVICE_PASSWORD || 'SECURE_PASSWORD_REQUIRED'`)
- [x] Redis REDACTED_SECRET (`process.env.REDIS_PASSWORD || 'SECURE_PASSWORD_REQUIRED'`)  
- [x] n8n admin REDACTED_SECRET (`n8n_secure_2024`)
- [x] API key placeholders (may contain real keys)

**Actions Taken:**
- [x] Immediate service shutdown
- [x] Password rotation for all services
- [x] API key regeneration  
- [x] Git history purged with git-filter-repo
- [x] Enhanced .gitignore and security documentation
- [x] Services restarted with new credentials

**Lessons Learned:**
- Implement pre-commit hooks to prevent secret commits
- Use secret management service for production deployments
- Regular security audits of version control history
- Team training on secure development practices

**Next Review Date:** `_________________`

---

## 🆘 EMERGENCY CONTACTS

If you encounter issues during rotation:

1. **Stop all services immediately** to prevent further exposure
2. **Contact system administrator** 
3. **Escalate to security team** if compromise suspected
4. **Document all actions taken** for incident response

**Remember:** When in doubt, err on the side of caution and rotate all potentially affected credentials.

---

✅ **ROTATION COMPLETE CHECKLIST:**
- [ ] All REDACTED_SECRETs rotated and tested
- [ ] API keys regenerated and configured  
- [ ] Git history cleaned and verified
- [ ] Services running with new credentials
- [ ] Team notified of changes
- [ ] Incident documented
- [ ] Long-term security measures implemented