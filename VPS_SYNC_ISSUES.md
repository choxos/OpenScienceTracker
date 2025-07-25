# VPS Site Not Matching Local Version - Quick Fix Guide

## 🚨 **Common Problem:**
After running `deploy.sh`, the VPS website doesn't show the latest changes (like dark theme improvements).

---

## ⚡ **Quick Solutions (In Order of Preference)**

### **🎯 Method 1: Force Sync Script (Recommended)**
```bash
cd /var/www/ost
git pull origin main
chmod +x force_sync_deployment.sh
sudo ./force_sync_deployment.sh
```

### **🔍 Method 2: Diagnosis First**
```bash
cd /var/www/ost
chmod +x diagnose_deployment.sh
./diagnose_deployment.sh
# Follow the recommendations it provides
```

### **🔧 Method 3: Manual Fix**
```bash
cd /var/www/ost
source ost_env/bin/activate

# Force static files collection
python manage.py collectstatic --noinput --clear

# Fix permissions
sudo chown -R www-data:www-data staticfiles/
sudo chmod -R 644 staticfiles/

# Restart services
sudo systemctl restart nginx
sudo systemctl restart ost-gunicorn

# Clear browser cache and test
```

---

## 🔍 **Root Causes & Quick Checks**

### **1. Static Files Not Updated**
**Check:** `ls -la staticfiles/css/dark-theme.css`
**Fix:** `python manage.py collectstatic --noinput --clear`

### **2. Permission Issues**
**Check:** `ls -ld staticfiles/`
**Fix:** `sudo chown -R www-data:www-data staticfiles/`

### **3. Services Not Restarted**
**Check:** `systemctl status nginx ost-gunicorn`
**Fix:** `sudo systemctl restart nginx ost-gunicorn`

### **4. Browser Cache**
**Check:** Open incognito/private browsing
**Fix:** Hard refresh (Ctrl+F5 or Cmd+Shift+R)

### **5. Nginx Configuration**
**Check:** `sudo nginx -t`
**Fix:** Verify static file location in Nginx config

---

## 🧪 **Verification Tests**

### **Test Static Files Directly:**
```bash
curl -I http://your-domain.com/static/css/dark-theme.css
# Should return HTTP 200 and show file size
```

### **Compare File Sizes:**
```bash
ls -la static/css/dark-theme.css
ls -la staticfiles/css/dark-theme.css
# Should be identical
```

### **Test Django Admin:**
```bash
# Open http://your-domain.com/admin/
# CSS should load properly if static files work
```

---

## 🚨 **Emergency Reset (Nuclear Option)**

If nothing else works:

```bash
cd /var/www/ost

# Reset everything
git reset --hard HEAD
git clean -fd
git pull origin main

# Rebuild static files from scratch
rm -rf staticfiles/*
source ost_env/bin/activate
python manage.py collectstatic --noinput --clear
sudo chown -R www-data:www-data staticfiles/

# Restart everything
sudo systemctl restart nginx
sudo systemctl restart ost-gunicorn

# Wait and test
sleep 10
curl -I http://localhost/static/css/dark-theme.css
```

---

## 🎯 **Most Likely Fixes**

**🥇 90% of cases:** Static files not collected or wrong permissions
**🥈 8% of cases:** Services not restarted properly  
**🥉 2% of cases:** Browser cache or Nginx configuration

---

## ✅ **Success Indicators**

### **✅ Fixed When You See:**
- Dark theme toggle works in browser
- CSS files load without 404 errors
- `curl -I http://your-domain.com/static/css/dark-theme.css` returns 200
- Website looks identical to local version

### **📱 Testing Checklist:**
- [ ] Homepage loads with proper styling
- [ ] Dark theme toggle button visible (bottom right)
- [ ] Dark theme actually changes appearance
- [ ] Fields page shows metric boxes correctly
- [ ] All pages maintain consistent styling
- [ ] Hard refresh doesn't break anything

---

## 🔧 **Prevention Tips**

### **Add to Deployment Routine:**
1. Always check static files after deployment
2. Test in incognito browser mode
3. Verify critical CSS files are accessible
4. Monitor service restart success

### **Automate Verification:**
```bash
# Add to deploy.sh end
echo "🧪 Testing static files..."
curl -f http://localhost/static/css/dark-theme.css > /dev/null && echo "✅ Static files OK" || echo "❌ Static files FAILED"
```

**💡 When in doubt, use the force sync script - it handles everything automatically!** 