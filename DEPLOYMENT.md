# Deploying to DigitalOcean App Platform

This guide will help you deploy the Zid Integration Service to DigitalOcean App Platform.

## Prerequisites

- DigitalOcean account
- GitHub repository with your code
- Zid app credentials (Client ID & Secret)

## Quick Deploy Steps

### 1. Push Code to GitHub

```bash
# Initialize git repository (if not already done)
git init
git add .
git commit -m "Initial commit: Zid Integration Service"

# Add your GitHub repository
git remote add origin https://github.com/YOUR_USERNAME/zid-integration.git
git branch -M main
git push -u origin main
```

### 2. Create App on DigitalOcean

**Option A: Using the DigitalOcean Control Panel**

1. Go to [DigitalOcean Apps](https://cloud.digitalocean.com/apps)
2. Click "Create App"
3. Connect your GitHub repository
4. Use the configuration from `.do/app.yaml`

**Option B: Using doctl CLI**

```bash
# Install doctl and authenticate
doctl apps create --spec .do/app.yaml
```

### 3. Configure Environment Variables

In the DigitalOcean App Platform dashboard, set these **ENCRYPTED** environment variables:

| Variable | Value | Notes |
|----------|--------|-------|
| `DATABASE_URL` | Auto-generated | Will be set by DO PostgreSQL |
| `ZID_CLIENT_ID` | `4968` | Your Zid app client ID |
| `ZID_CLIENT_SECRET` | `f9JNgI5vlfTJMa6gaBUpD8gjibyeT4x6khZmpt9M` | Your Zid app secret |
| `ZID_REDIRECT_URI` | `https://your-app-name.ondigitalocean.app/auth/callback` | Update with your app URL |
| `SECRET_KEY` | Generate new secure key | For JWT signing |
| `ENVIRONMENT` | `production` | Enables production mode |

### 4. Update Zid App Configuration

1. Go to your Zid Developer Dashboard
2. Update your app's redirect URI to: `https://your-app-name.ondigitalocean.app/auth/callback`
3. Add your production domain to allowed origins if needed

### 5. Deploy

The app will automatically deploy when you:
- Push code to the `main` branch
- Or manually trigger deployment in DO dashboard

## Post-Deployment

### Verify Deployment

1. **Health Check**: Visit `https://your-app-name.ondigitalocean.app/health`
2. **API Docs**: Visit `https://your-app-name.ondigitalocean.app/docs`
3. **OAuth Flow**: Visit `https://your-app-name.ondigitalocean.app/auth/authorize`

### Test OAuth Integration

```bash
# Get authorization URL
curl https://your-app-name.ondigitalocean.app/auth/authorize

# Test webhook endpoint
curl -X POST https://your-app-name.ondigitalocean.app/webhooks/zid \
  -H "Content-Type: application/json" \
  -d '{"event":"order.created","id":"test_123","merchant_id":"test"}'
```

## Production Configuration

### Environment Settings

The app automatically detects production environment and:
- ✅ Disables SQL query logging
- ✅ Optimizes database connection pooling
- ✅ Configures proper CORS origins
- ✅ Enables production-grade error handling

### Security

- All sensitive environment variables are encrypted
- Database connections use SSL by default
- CORS is restricted in production
- Comprehensive input validation

### Monitoring

DigitalOcean provides built-in monitoring:
- **Metrics**: CPU, Memory, Request rate
- **Logs**: Application and access logs
- **Alerts**: Configure alerts for high error rates
- **Health Checks**: Automatic `/health` endpoint monitoring

## Scaling

### Vertical Scaling
- Upgrade instance size in DO dashboard
- Available sizes: basic-xxs, basic-xs, basic-s, basic-m

### Horizontal Scaling
- Increase instance count in app.yaml
- Load balancing is automatic

### Database Scaling
- Upgrade PostgreSQL instance size
- Enable read replicas for high-traffic scenarios

## Troubleshooting

### Common Issues

**1. Environment Variables Not Loading**
```bash
# Check app logs
doctl apps logs YOUR_APP_ID --follow
```

**2. Database Connection Issues**
- Verify DATABASE_URL is set correctly
- Check database is in same region as app

**3. OAuth Redirect Issues**
- Verify ZID_REDIRECT_URI matches your domain
- Update Zid app configuration

**4. Migration Failures**
```bash
# Run migration manually
doctl apps create-deployment YOUR_APP_ID --force-rebuild
```

### Support

- DigitalOcean Support: [DO Community](https://www.digitalocean.com/community)
- App Platform Docs: [DO App Platform](https://docs.digitalocean.com/products/app-platform/)

## Cost Estimation

**Basic Setup:**
- App (basic-xxs): ~$5/month
- PostgreSQL (basic): ~$15/month
- **Total**: ~$20/month

**Production Setup:**
- App (basic-s): ~$25/month  
- PostgreSQL (pro): ~$50/month
- **Total**: ~$75/month

## Backup & Recovery

- Database backups are automatic (7-day retention)
- App configuration is version controlled in GitHub
- Environment variables should be documented securely

## Updates

```bash
# Deploy updates
git add .
git commit -m "Update: description"
git push origin main
# Auto-deploys to production
```