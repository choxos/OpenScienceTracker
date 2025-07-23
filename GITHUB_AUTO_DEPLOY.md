# 🚀 GitHub Auto-Deploy to Hetzner VPS

Set up automatic deployment from GitHub to your Hetzner VPS whenever you push code - just like Railway!

## 🎯 Overview

This setup will:
- ✅ **Auto-deploy** on every push to `main` branch
- ✅ **Run migrations** automatically
- ✅ **Restart services** after deployment
- ✅ **Zero downtime** deployment process
- ✅ **Rollback capability** if needed

## 🔐 Step 1: Set Up SSH Key for GitHub Actions

### On Your VPS:

```bash
# SSH into your VPS
ssh xeradb@91.99.161.136

# Create a dedicated deployment key
ssh-keygen -t ed25519 -C "github-deploy@xeradb" -f ~/.ssh/github_deploy_key

# Add the public key to authorized_keys
cat ~/.ssh/github_deploy_key.pub >> ~/.ssh/authorized_keys

# Display the private key (copy this for GitHub Secrets)
echo "=== COPY THIS PRIVATE KEY FOR GITHUB SECRETS ==="
cat ~/.ssh/github_deploy_key
echo "=== END PRIVATE KEY ==="

# Set proper permissions
chmod 600 ~/.ssh/github_deploy_key
chmod 600 ~/.ssh/authorized_keys
```

### In Your GitHub Repository:

1. Go to your repository: `https://github.com/choxos/OpenScienceTracker`
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add these secrets:

| Secret Name | Value |
|-------------|-------|
| `VPS_HOST` | `91.99.161.136` |
| `VPS_USER` | `xeradb` |
| `VPS_SSH_KEY` | *Private key content from above* |
| `VPS_PORT` | `22` |

## 📁 Step 2: Create Deployment Script on VPS

```bash
# Create deployment script directory
mkdir -p /var/www/shared/scripts
cd /var/www/shared/scripts

# Create the deployment script
cat > deploy-ost.sh << 'EOF'
#!/bin/bash
set -e

echo "🚀 Starting OST deployment..."
echo "Time: $(date)"

# Configuration
PROJECT_DIR="/var/www/ost"
SERVICE_NAME="ost"
BACKUP_DIR="/var/www/backups/auto-deploy"

# Create backup directory
mkdir -p $BACKUP_DIR

# Function to log with timestamp
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Function to rollback if deployment fails
rollback() {
    log "❌ Deployment failed! Rolling back..."
    if [ -f "$BACKUP_DIR/latest_working.tar.gz" ]; then
        cd /var/www
        tar -xzf "$BACKUP_DIR/latest_working.tar.gz"
        sudo systemctl restart $SERVICE_NAME
        log "✅ Rollback completed"
    fi
    exit 1
}

# Set up error handling
trap rollback ERR

log "📦 Creating backup of current version..."
cd /var/www
tar -czf "$BACKUP_DIR/backup_$(date +%Y%m%d_%H%M%S).tar.gz" ost/
cp "$BACKUP_DIR/backup_$(date +%Y%m%d_%H%M%S).tar.gz" "$BACKUP_DIR/latest_working.tar.gz"

log "📥 Pulling latest code..."
cd $PROJECT_DIR
git fetch origin
git reset --hard origin/main

log "🐍 Updating Python dependencies..."
source venv/bin/activate
pip install -r requirements.txt

log "🗄️ Running database migrations..."
export DJANGO_SETTINGS_MODULE=ost_web.production_settings
export RAILWAY_ENVIRONMENT=production
python manage.py migrate

log "📊 Collecting static files..."
python manage.py collectstatic --noinput

log "🔄 Restarting application service..."
sudo systemctl restart $SERVICE_NAME

log "⏳ Waiting for service to start..."
sleep 5

log "🔍 Checking service status..."
if sudo systemctl is-active --quiet $SERVICE_NAME; then
    log "✅ Service is running"
else
    log "❌ Service failed to start"
    sudo journalctl -u $SERVICE_NAME --no-pager --lines=20
    rollback
fi

log "🌐 Testing application health..."
if curl -f -s http://localhost:8000/ > /dev/null; then
    log "✅ Application is responding"
else
    log "❌ Application health check failed"
    rollback
fi

log "🧹 Cleaning up old backups (keep last 5)..."
cd $BACKUP_DIR
ls -t backup_*.tar.gz | tail -n +6 | xargs -r rm

log "🎉 Deployment completed successfully!"
echo "📊 Database status:"
cd $PROJECT_DIR
source venv/bin/activate
python manage.py shell -c "
from tracker.models import Journal, Paper
print(f'📚 Journals: {Journal.objects.count():,}')
print(f'📄 Papers: {Paper.objects.count():,}')
"

EOF

# Make script executable
chmod +x deploy-ost.sh

# Test the script permissions
ls -la deploy-ost.sh
```

## 🔧 Step 3: Configure Sudo Permissions

```bash
# Allow xeradb user to restart services without password
echo "xeradb ALL=(ALL) NOPASSWD: /bin/systemctl restart ost, /bin/systemctl status ost, /bin/systemctl is-active ost, /bin/journalctl" | sudo tee /etc/sudoers.d/xeradb-deploy

# Test sudo permissions
sudo systemctl status ost
```

## 📋 Step 4: Create GitHub Actions Workflow

**Create the workflow file in your local repository:**

```bash
# On your local machine
cd /Users/choxos/Documents/GitHub/OpenScienceTracker

# Create GitHub Actions directory
mkdir -p .github/workflows

# Create the deployment workflow
cat > .github/workflows/deploy-to-hetzner.yml << 'EOF'
name: 🚀 Deploy to Hetzner VPS

on:
  push:
    branches: [ main ]
  workflow_dispatch:  # Allow manual triggering

jobs:
  deploy:
    name: Deploy to Production
    runs-on: ubuntu-latest
    
    steps:
    - name: 📥 Checkout code
      uses: actions/checkout@v4
      
    - name: 🔐 Setup SSH
      uses: webfactory/ssh-agent@v0.8.0
      with:
        ssh-private-key: ${{ secrets.VPS_SSH_KEY }}
        
    - name: 📋 Add VPS to known hosts
      run: |
        ssh-keyscan -H ${{ secrets.VPS_HOST }} >> ~/.ssh/known_hosts
        
    - name: 🚀 Deploy to VPS
      run: |
        ssh -o StrictHostKeyChecking=no ${{ secrets.VPS_USER }}@${{ secrets.VPS_HOST }} \
          'bash /var/www/shared/scripts/deploy-ost.sh'
        
    - name: 🔍 Verify deployment
      run: |
        ssh -o StrictHostKeyChecking=no ${{ secrets.VPS_USER }}@${{ secrets.VPS_HOST }} \
          'curl -f http://localhost:8000/ && echo "✅ Application is live!"'
        
    - name: 📊 Report status
      run: |
        ssh -o StrictHostKeyChecking=no ${{ secrets.VPS_USER }}@${{ secrets.VPS_HOST }} \
          'cd /var/www/ost && source venv/bin/activate && python manage.py shell -c "
          from tracker.models import Journal, Paper
          print(f\"📚 Journals: {Journal.objects.count():,}\")
          print(f\"📄 Papers: {Paper.objects.count():,}\")
          "'
EOF
```

## 🎛️ Step 5: Advanced Deployment Options

### Enable Slack/Discord Notifications

```yaml
# Add to the end of deploy-to-hetzner.yml
    - name: 📢 Notify Slack (on success)
      if: success()
      uses: 8398a7/action-slack@v3
      with:
        status: success
        text: '✅ OST deployed successfully to Hetzner VPS!'
      env:
        SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
        
    - name: 📢 Notify Slack (on failure)
      if: failure()
      uses: 8398a7/action-slack@v3
      with:
        status: failure
        text: '❌ OST deployment failed!'
      env:
        SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
```

### Conditional Deployment (Staging vs Production)

```yaml
# Add environment-based deployment
    - name: 🎯 Deploy to Staging
      if: github.ref == 'refs/heads/develop'
      run: |
        ssh ${{ secrets.VPS_USER }}@${{ secrets.VPS_HOST }} \
          'bash /var/www/shared/scripts/deploy-ost-staging.sh'
          
    - name: 🚀 Deploy to Production
      if: github.ref == 'refs/heads/main'
      run: |
        ssh ${{ secrets.VPS_USER }}@${{ secrets.VPS_HOST }} \
          'bash /var/www/shared/scripts/deploy-ost.sh'
```

## 🔄 Step 6: Test the Auto-Deployment

```bash
# Commit and push the workflow
git add .github/workflows/deploy-to-hetzner.yml
git commit -m "🚀 Add GitHub Actions auto-deployment to Hetzner VPS

- Automatic deployment on push to main branch
- SSH-based secure deployment with rollback capability
- Service restart and health checks
- Database migration automation
- Backup creation before each deployment"

git push origin main
```

## 📊 Step 7: Monitor Deployments

### Check GitHub Actions:
1. Go to your repository
2. Click **Actions** tab
3. Watch the deployment progress in real-time

### Monitor on VPS:
```bash
# Watch deployment logs in real-time
ssh xeradb@91.99.161.136
tail -f /var/log/syslog | grep deploy

# Check service status
sudo systemctl status xeradb-ost

# View application logs
sudo journalctl -u xeradb-ost -f
```

## 🛠️ Step 8: Additional Deployment Features

### Zero-Downtime Deployment (Blue-Green)

```bash
# Create blue-green deployment script
cat > /var/www/shared/scripts/deploy-ost-zero-downtime.sh << 'EOF'
#!/bin/bash
# Blue-Green deployment for zero downtime

CURRENT_PORT=$(curl -s http://localhost:8000 && echo "8000" || echo "8001")
NEW_PORT=$([[ $CURRENT_PORT == "8000" ]] && echo "8001" || echo "8000")

echo "🔄 Deploying to port $NEW_PORT (current: $CURRENT_PORT)"

# Deploy to new port
# Update gunicorn config to use new port
sed -i "s/127.0.0.1:$CURRENT_PORT/127.0.0.1:$NEW_PORT/" gunicorn.conf.py

# Start new instance
gunicorn --config gunicorn.conf.py ost_web.wsgi:application &

# Wait and test new instance
sleep 10
if curl -f http://localhost:$NEW_PORT/; then
    # Update nginx to point to new port
    sudo sed -i "s/127.0.0.1:$CURRENT_PORT/127.0.0.1:$NEW_PORT/" /etc/nginx/sites-available/ost
    sudo nginx -s reload
    
    # Stop old instance
    pkill -f "gunicorn.*$CURRENT_PORT"
    echo "✅ Zero-downtime deployment complete"
else
    echo "❌ New instance failed, keeping current"
    pkill -f "gunicorn.*$NEW_PORT"
fi
EOF
```

### Database Backup Before Deployment

```bash
# Add to deployment script
cat >> /var/www/shared/scripts/deploy-ost.sh << 'EOF'

# Database backup before deployment
log "💾 Creating database backup..."
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
pg_dump -h localhost -U ost_user ost_production > /var/www/backups/auto-deploy/db_backup_$TIMESTAMP.sql
log "✅ Database backup completed: db_backup_$TIMESTAMP.sql"
EOF
```

## 🎉 Result

You now have:
- ✅ **Automatic deployment** on every push to main
- ✅ **Rollback capability** if deployment fails
- ✅ **Health checks** to verify successful deployment
- ✅ **Service management** with proper restarts
- ✅ **Database migration** automation
- ✅ **Backup creation** before each deployment
- ✅ **Real-time monitoring** through GitHub Actions

Your **Hetzner VPS** now works just like **Railway** with automatic deployments! 🚀

### 🎯 Next Steps:
1. **Test the deployment** by making a small change and pushing
2. **Set up branch protection** to require successful deployment
3. **Add monitoring alerts** for failed deployments
4. **Configure staging environment** for testing before production 