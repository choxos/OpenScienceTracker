# 🚀 REST API Deployment Guide

## Overview

This guide will help you deploy the new REST API to your Hetzner VPS. The API provides comprehensive programmatic access to OST data for external researchers.

## 🔧 Deployment Steps

### 1. Pull Latest Code

```bash
# Connect to your VPS
ssh xeradb@91.99.161.136

# Navigate to the application directory
cd /var/www/ost

# Pull the latest code with API
git pull origin main
```

### 2. Install New Dependencies

```bash
# Activate virtual environment
source venv/bin/activate

# Install new API dependencies
pip install djangorestframework==3.15.2
pip install django-filter==24.3
pip install django-cors-headers==4.6.0
pip install drf-spectacular==0.28.0

# Or install from requirements.txt
pip install -r requirements.txt
```

### 3. Update Django Settings

The API configuration is already added to `settings.py`. Verify the following are included:

```python
INSTALLED_APPS = [
    # ... existing apps ...
    'rest_framework',
    'django_filters', 
    'corsheaders',
    'drf_spectacular',
    'tracker',
]

MIDDLEWARE = [
    # ... existing middleware ...
    'corsheaders.middleware.CorsMiddleware',  # Should be near the top
    # ... rest of middleware ...
]
```

### 4. Run Database Migrations (if any)

```bash
python manage.py migrate
```

### 5. Collect Static Files

```bash
python manage.py collectstatic --noinput
```

### 6. Test the API Locally

```bash
# Test Django configuration
python manage.py check

# Start development server for testing (optional)
python manage.py runserver 127.0.0.1:8001

# In another terminal, test API endpoints
curl http://127.0.0.1:8001/api/
curl http://127.0.0.1:8001/api/v1/papers/?page_size=5
```

### 7. Restart Production Services

```bash
# Restart Gunicorn
sudo systemctl restart ost

# Restart Nginx
sudo systemctl restart nginx

# Check service status
sudo systemctl status ost
sudo systemctl status nginx
```

## 🌐 Test API Endpoints

After deployment, test these endpoints:

### 1. API Overview
```bash
curl https://ost.xeradb.com/api/
```

### 2. Interactive Documentation
Visit in browser:
- https://ost.xeradb.com/api/docs/ (Swagger UI)
- https://ost.xeradb.com/api/redoc/ (ReDoc)

### 3. Sample API Calls
```bash
# Get first 5 papers
curl "https://ost.xeradb.com/api/v1/papers/?page_size=5"

# Get transparency statistics
curl "https://ost.xeradb.com/api/v1/papers/transparency_stats/"

# Get journals with at least 100 papers
curl "https://ost.xeradb.com/api/v1/journals/?min_papers=100&page_size=5"

# Search for specific papers
curl "https://ost.xeradb.com/api/v1/papers/?search=COVID&page_size=3"
```

## 📊 Expected API Response

### API Overview (`/api/`)
```json
{
  "api_info": {
    "name": "Open Science Tracker API",
    "version": "1.0.0",
    "description": "REST API for accessing transparency and reproducibility data from medical and dental literature"
  },
  "statistics": {
    "total_papers": 1108842,
    "total_journals": 11236,
    "total_research_fields": 125,
    "transparency_coverage": {
      "open_data": 45231,
      "open_code": 12456,
      "conflict_of_interest": 892341,
      "funding_declaration": 756892,
      "registration": 234567,
      "reporting_guidelines": 445233,
      "data_sharing": 334455
    }
  },
  "available_endpoints": {
    "papers": "https://ost.xeradb.com/api/v1/papers/",
    "journals": "https://ost.xeradb.com/api/v1/journals/",
    "research_fields": "https://ost.xeradb.com/api/v1/research-fields/",
    "schema": "https://ost.xeradb.com/api/schema/",
    "documentation": "https://ost.xeradb.com/api/docs/"
  }
}
```

## 🔧 Troubleshooting

### Issue 1: Missing Dependencies
```bash
# Error: No module named 'rest_framework'
# Solution: Install dependencies
pip install -r requirements.txt
```

### Issue 2: Database Migration Needed
```bash
# Error: django.db.utils.ProgrammingError
# Solution: Run migrations
python manage.py migrate
```

### Issue 3: Static Files Not Found
```bash
# Error: 404 for /api/docs/ styles
# Solution: Collect static files
python manage.py collectstatic --noinput
sudo systemctl restart ost
```

### Issue 4: CORS Issues in Browser
```bash
# Error: CORS policy blocks request
# Solution: Verify CORS settings in settings.py
# Should include: CORS_ALLOW_ALL_ORIGINS = True
```

### Issue 5: Rate Limiting
```bash
# Error: "Request was throttled"
# Solution: Rate limit is 1000/day per IP
# For higher limits, contact for API key support
```

## ⚡ Performance Optimization

### 1. Enable Database Query Caching
The API already includes caching for expensive operations:
- Overview statistics: 30 minutes
- Transparency stats: 15 minutes

### 2. Monitor API Performance
```bash
# Check API response times
curl -w "@curl-format.txt" -o /dev/null "https://ost.xeradb.com/api/v1/papers/?page_size=50"

# Create curl-format.txt:
echo "     time_namelookup:  %{time_namelookup}\n
         time_connect:  %{time_connect}\n
      time_appconnect:  %{time_appconnect}\n
     time_pretransfer:  %{time_pretransfer}\n
        time_redirect:  %{time_redirect}\n
   time_starttransfer:  %{time_starttransfer}\n
                     \\n
           time_total:  %{time_total}\n" > curl-format.txt
```

### 3. Database Indexing
Key database indexes are already in place:
- PMID (primary key)
- Publication year
- Journal foreign key
- Transparency boolean fields

## 🌟 API Features Summary

### ✅ Available Endpoints:
- `/api/` - API overview and statistics
- `/api/v1/papers/` - Research papers with filtering
- `/api/v1/journals/` - Journals with statistics
- `/api/v1/research-fields/` - Research field categories
- `/api/docs/` - Interactive Swagger documentation
- `/api/redoc/` - Alternative ReDoc documentation

### ✅ Advanced Features:
- **Filtering**: By year, journal, transparency score, author, etc.
- **Search**: Full-text search in titles, abstracts, authors
- **Pagination**: Efficient handling of large result sets
- **Statistics**: Real-time transparency statistics
- **Export**: JSON/JSONL format for analysis
- **Documentation**: Interactive API explorer

### ✅ Research Applications:
- Meta-analysis data collection
- Transparency trend analysis
- Journal policy comparison
- Bibliometric research
- Open science studies

## 🎯 Next Steps

1. **Test all endpoints** to ensure they work correctly
2. **Share API documentation** with potential research collaborators
3. **Monitor usage** and performance
4. **Consider API key system** for higher rate limits if needed
5. **Add API usage examples** to your research publications

## 📞 Support

If you encounter any issues:
- Check the logs: `sudo journalctl -u ost -f`
- Verify Nginx config: `sudo nginx -t`
- Test Django: `python manage.py check`
- Contact: ahmad.pub@gmail.com

---

🎉 **Congratulations!** Your Open Science Tracker now has a world-class REST API for researchers to access transparency data programmatically! 