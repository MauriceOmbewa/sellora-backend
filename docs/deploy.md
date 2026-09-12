# Sellora Backend — Production Deploy Checklist

## Environment Variables (required in production)

```bash
DJANGO_SETTINGS_MODULE=config.settings.production
DJANGO_SECRET_KEY=<long-random-string>           # python -c "import secrets; print(secrets.token_urlsafe(50))"
DJANGO_ALLOWED_HOSTS=api.yourdomain.com
DATABASE_URL=postgres://user:pass@host:5432/sellora_prod
REDIS_URL=redis://host:6379/0
CELERY_BROKER_URL=redis://host:6379/0
CELERY_RESULT_BACKEND=redis://host:6379/1
GOOGLE_CLIENT_ID=<from Google Cloud Console>
GOOGLE_CLIENT_SECRET=<from Google Cloud Console>
GOOGLE_REDIRECT_URI=https://api.yourdomain.com/api/v1/auth/google/callback/
FRONTEND_WEB_URL=https://app.yourdomain.com
APP_DEEP_LINK_SCHEME=sellora
USE_S3=True
AWS_ACCESS_KEY_ID=<key>
AWS_SECRET_ACCESS_KEY=<secret>
AWS_STORAGE_BUCKET_NAME=sellora-media
AWS_S3_REGION_NAME=us-east-1
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_HOST_USER=<email>
EMAIL_HOST_PASSWORD=<app-password>
DEFAULT_FROM_EMAIL=Sellora <noreply@yourdomain.com>
SENTRY_DSN=<optional>
```

## First Deploy Steps

```bash
# 1. Collect static files
python manage.py collectstatic --noinput

# 2. Apply migrations
python manage.py migrate

# 3. Create superuser (for Django admin)
SUPERUSER_EMAIL=admin@yourdomain.com python manage.py shell < scripts/create_superuser.py
```

## Running Services

### Gunicorn (WSGI server)
```bash
gunicorn config.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers 4 \
  --worker-class sync \
  --timeout 120 \
  --access-logfile - \
  --error-logfile -
```

### Celery worker
```bash
celery -A config.celery worker \
  --loglevel=info \
  --concurrency=4 \
  --queues=default
```

### Celery beat (scheduled tasks)
```bash
celery -A config.celery beat \
  --loglevel=info
```

## Google Cloud Console Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a project → Enable **Google+ API** and **Google Identity API**
3. Credentials → Create OAuth 2.0 Client ID (Web application)
4. Authorized redirect URIs: `https://api.yourdomain.com/api/v1/auth/google/callback/`
5. Copy Client ID and Client Secret → add to `.env`

## Security Checklist

- [ ] `SECRET_KEY` is long, random, and not committed to git
- [ ] `DEBUG=False` in production
- [ ] `ALLOWED_HOSTS` is set to your actual domain
- [ ] PostgreSQL user has minimal required permissions
- [ ] SSL certificate installed (HTTPS enforced)
- [ ] `SECURE_SSL_REDIRECT=True` (set in production.py)
- [ ] HSTS enabled (`SECURE_HSTS_SECONDS=31536000`)
- [ ] S3 bucket is private; media served via signed URLs or CloudFront
- [ ] Sentry DSN configured for error monitoring
- [ ] Redis protected with AUTH password in production
- [ ] Database backups configured

## Nginx Configuration (example)

```nginx
server {
    listen 443 ssl;
    server_name api.yourdomain.com;

    ssl_certificate /etc/ssl/certs/yourdomain.pem;
    ssl_certificate_key /etc/ssl/private/yourdomain.key;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /media/ {
        # In production, serve media from S3/CloudFront instead
        alias /app/media/;
    }
}
```
