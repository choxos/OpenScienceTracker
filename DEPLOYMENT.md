# 🚀 Railway Deployment Guide for Open Science Tracker

## Quick Deploy to Railway

### 1. **Environment Variables**
Set these environment variables in your Railway project:

```bash
# Required
SECRET_KEY=your-super-secret-key-here-change-this
DEBUG=False

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

2. **Import Data** (if needed):
   ```bash
   python import_dental_data_fixed.py
   python import_europe_pmc_data.py
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