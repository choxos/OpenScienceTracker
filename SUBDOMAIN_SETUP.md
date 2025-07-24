# 🌐 Setting Up ost.xeradb.com Subdomain

## Overview

This guide walks you through setting up `ost.xeradb.com` to point to your Open Science Tracker on Hetzner VPS.

## 📋 Prerequisites

- Your Hetzner VPS IP: `91.99.161.136`
- Domain control for `xeradb.com`
- SSH access to your VPS

## 🔧 Step 1: DNS Configuration

### Option A: Using Your Domain Registrar's DNS Panel

1. **Login to your domain registrar** (where you bought `xeradb.com`)
2. **Find DNS Management** (might be called "DNS Records", "Zone File", etc.)
3. **Add an A Record**:
   - **Type**: A
   - **Name**: `ost` (or `ost.xeradb.com` depending on interface)
   - **Value/Points to**: `91.99.161.136`
   - **TTL**: 300 or 3600 (5 minutes or 1 hour)

### Option B: Using Cloudflare (Recommended)

If you use Cloudflare for DNS:

1. **Login to Cloudflare Dashboard**
2. **Select your domain**: `xeradb.com`
3. **Go to DNS Records**
4. **Add Record**:
   - **Type**: A
   - **Name**: `ost`
   - **IPv4 address**: `91.99.161.136`
   - **Proxy status**: 🟠 DNS only (for initial setup)
   - **TTL**: Auto

### Verify DNS Propagation

Wait 5-15 minutes, then test:

```bash
# Test DNS resolution
nslookup ost.xeradb.com
dig ost.xeradb.com

# Should return: 91.99.161.136
```

## 🌐 Step 2: Nginx Configuration

### Update Nginx Virtual Host

```bash
# Connect to your VPS
ssh xeradb@91.99.161.136

# Edit the existing Nginx configuration
sudo nano /etc/nginx/sites-available/ost
```

**Update the configuration to include your domain:**

```nginx
server {
    listen 80;
    server_name ost.xeradb.com 91.99.161.136;

    client_max_body_size 100M;

    location = /favicon.ico { 
        access_log off; 
        log_not_found off; 
    }
    
    location /static/ {
        root /var/www/ost;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
    
    location /media/ {
        root /var/www/ost;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location / {
        include proxy_params;
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Test and Restart Nginx

```bash
# Test the configuration
sudo nginx -t

# Restart Nginx if test passes
sudo systemctl restart nginx

# Check status
sudo systemctl status nginx
```

## ⚙️ Step 3: Update Django Settings

### Update Allowed Hosts

```bash
# Edit your environment file
nano /var/www/ost/.env
```

**Update the ALLOWED_HOSTS line:**

```bash
ALLOWED_HOSTS=ost.xeradb.com,xeradb.com,91.99.161.136,localhost
```

### Restart OST Service

```bash
# Restart your application to pick up the new settings
sudo systemctl restart ost

# Verify it's running
sudo systemctl status ost
curl -f http://localhost:8000/
```

## 🔒 Step 4: SSL Certificate with Let's Encrypt

### Install Certbot (if not already installed)

```bash
# Install Certbot
sudo apt update
sudo apt install snapd
sudo snap install core; sudo snap refresh core
sudo snap install --classic certbot

# Create symlink
sudo ln -s /snap/bin/certbot /usr/bin/certbot
```

### Get SSL Certificate

```bash
# Get certificate for your domain
sudo certbot --nginx -d ost.xeradb.com

# Follow the prompts:
# 1. Enter email address
# 2. Agree to terms
# 3. Choose whether to share email (optional)
# 4. Choose redirect option (recommended: redirect HTTP to HTTPS)
```

### Test Auto-Renewal

```bash
# Test automatic renewal
sudo certbot renew --dry-run

# Check renewal timer
sudo systemctl status snap.certbot.renew.timer
```

## ✅ Step 5: Verify Everything Works

### Test Your Website

```bash
# Test HTTP (should redirect to HTTPS)
curl -I http://ost.xeradb.com

# Test HTTPS
curl -I https://ost.xeradb.com

# Test from your local machine
open https://ost.xeradb.com
```

### Final Nginx Configuration Check

Your final Nginx config should look like this after Certbot:

```bash
# View the updated config
sudo cat /etc/nginx/sites-available/ost
```

Expected configuration after SSL:

```nginx
server {
    server_name ost.xeradb.com 91.99.161.136;

    client_max_body_size 100M;

    location = /favicon.ico { 
        access_log off; 
        log_not_found off; 
    }
    
    location /static/ {
        root /var/www/ost;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
    
    location /media/ {
        root /var/www/ost;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location / {
        include proxy_params;
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    listen 443 ssl; # managed by Certbot
    ssl_certificate /etc/letsencrypt/live/ost.xeradb.com/fullchain.pem; # managed by Certbot
    ssl_certificate_key /etc/letsencrypt/live/ost.xeradb.com/privkey.pem; # managed by Certbot
    include /etc/letsencrypt/options-ssl-nginx.conf; # managed by Certbot
    ssl_dhparam /etc/letsencrypt/options-ssl-dhparam.pem; # managed by Certbot
}

server {
    if ($host = ost.xeradb.com) {
        return 301 https://$host$request_uri;
    } # managed by Certbot

    listen 80;
    server_name ost.xeradb.com 91.99.161.136;
    return 404; # managed by Certbot
}
```

## 🔄 Step 6: Update GitHub Auto-Deployment

Update your deployment script to use the new domain for health checks:

```bash
# Edit the deployment script
nano /var/www/shared/scripts/deploy-ost.sh
```

**Update the health check section:**

```bash
log "🌐 Testing application health..."
if curl -f -s https://ost.xeradb.com/ > /dev/null; then
    log "✅ Application is responding at https://ost.xeradb.com"
elif curl -f -s http://localhost:8000/ > /dev/null; then
    log "✅ Application is responding locally"
else
    log "❌ Application health check failed"
    rollback
fi
```

## 🎯 Verification Checklist

After completing all steps, verify:

- [ ] `https://ost.xeradb.com` loads your Open Science Tracker
- [ ] SSL certificate is valid (green padlock in browser)
- [ ] HTTP automatically redirects to HTTPS
- [ ] All static files (CSS, JS, images) load correctly
- [ ] Admin interface works: `https://ost.xeradb.com/admin/`
- [ ] API endpoints respond correctly

## 🛠️ Troubleshooting

### DNS Issues
```bash
# Check DNS propagation
dig ost.xeradb.com
nslookup ost.xeradb.com 8.8.8.8
```

### Nginx Issues
```bash
# Check Nginx logs
sudo tail -f /var/log/nginx/error.log
sudo tail -f /var/log/nginx/access.log
```

### SSL Issues
```bash
# Check certificate status
sudo certbot certificates
openssl s_client -connect ost.xeradb.com:443
```

### Django Issues
```bash
# Check application logs
sudo journalctl -u ost -f
```

## 🎉 Success!

Your Open Science Tracker should now be accessible at:
- **🌐 Main URL**: `https://ost.xeradb.com`
- **🔒 Secure**: SSL/TLS encrypted
- **📱 Mobile-friendly**: Responsive design
- **⚡ Fast**: Nginx static file serving
- **🔄 Auto-deploying**: GitHub Actions integration

---

**Next Steps**: Consider setting up monitoring, analytics, and backup automation for your production deployment! 