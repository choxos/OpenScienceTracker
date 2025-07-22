# 🚀 Railway Deployment Guide for Open Science Tracker

## Quick Deploy to Railway with PostgreSQL Database

### 1. **Create Railway Project with PostgreSQL**
1. Go to [Railway.app](https://railway.app)
2. Create new project
3. Add PostgreSQL database service
4. Connect your GitHub repository

### 2. **Environment Variables**
Set these environment variables in your Railway project:

```bash
# Required
SECRET_KEY=!t8()9=h3v37))_8b2ih__h79e+uolpynme@(w(j50n2_7(ze#
DEBUG=False

# Database (automatically set by Railway PostgreSQL service)
DATABASE_URL=postgresql://user:pass@host:port/dbname

# Optional (defaults work for most cases)
ALLOWED_HOSTS=*.railway.app,.railway.app,yourdomain.com
```

### 2. **Generate Secret Key**
Generate a secure secret key for production:

```python
from django.core.management.utils import get_random_secret_key
print(get_random_secret_key())
```

### 3. **Deploy Steps**
1. Fork this repository
2. Connect your Railway account to GitHub
3. Create a new Railway project from your forked repository
4. Set the environment variables listed above
5. Railway will automatically:
   - Install dependencies from `requirements.txt`
   - Run database migrations
   - Collect static files
   - Start the application with gunicorn

### 4. **Post-Deployment Setup**
After successful deployment:

1. **Create Superuser** (via Railway console):
   ```bash
   python manage.py createsuperuser
   ```

2. **Import OST Data** (includes medical + dental transparency data):
   
   **Option A: Import from GitHub Release** (Recommended)
   ```bash
   # Download data files from GitHub releases
   python import_data_to_railway.py
   ```
   
   **Option B: Import from Local Export**
   If you have exported data locally:
   ```bash
   # First export data locally:
   python export_data_for_railway.py
   
   # Then upload railway_data/ folder and run:
   python import_data_to_railway.py
   ```
   
   **Option C: Import from Original Data Sources**
   ```bash
   # Download medical transparency data from OSF:
   # https://osf.io/zbc6p/files/osfstorage/66113e60c0539424e0b4d499
   # Save as papers/medicaltransparency_opendata.csv
   
   # Run the import scripts:
   python import_all_journals.py
   python import_medical_transparency_data.py
   ```

### 5. **Health Check**
Visit `https://yourdomain.railway.app/health/` to verify the deployment is working.

### 6. **Static Files**
Static files are automatically handled by WhiteNoise middleware in production.

## Configuration Files

- **`Procfile`**: Defines the web process command
- **`railway.json`**: Railway-specific deployment configuration
- **`requirements.txt`**: Python dependencies including gunicorn and whitenoise
- **`ost_web/settings.py`**: Production-ready Django settings

## Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SECRET_KEY` | ✅ | Development key | Django secret key for production |
| `DEBUG` | ❌ | `True` | Set to `False` for production |
| `ALLOWED_HOSTS` | ❌ | Railway domains | Comma-separated list of allowed hosts |

## Troubleshooting

### Common Issues:

1. **"gunicorn: command not found"**
   - Ensure `gunicorn==23.0.0` is in `requirements.txt`
   - Redeploy the application

2. **Static files not loading**
   - WhiteNoise middleware should handle this automatically
   - Check that `STATIC_ROOT` is set correctly

3. **Database migration errors**
   - Railway runs migrations automatically
   - Check deployment logs for specific errors

4. **Health check failing**
   - Visit `/health/` endpoint to see the error
   - Check database connectivity

### Support

For deployment issues:
- Check Railway deployment logs
- Verify all environment variables are set
- Ensure the health check endpoint returns 200 OK

---

**Built with ❤️ for Open Science** 