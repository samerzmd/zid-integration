#!/bin/bash

# Zid Integration Service - DigitalOcean Deployment Script
# Usage: ./deploy.sh

set -e

echo "🚀 Deploying Zid Integration Service to DigitalOcean App Platform"

# Check if doctl is installed
if ! command -v doctl &> /dev/null; then
    echo "❌ doctl CLI not found. Please install it first:"
    echo "   https://docs.digitalocean.com/reference/doctl/how-to/install/"
    exit 1
fi

# Check if user is authenticated
if ! doctl account get &> /dev/null; then
    echo "❌ Please authenticate with DigitalOcean first:"
    echo "   doctl auth init"
    exit 1
fi

# Validate app.yaml exists
if [ ! -f ".do/app.yaml" ]; then
    echo "❌ .do/app.yaml not found. Please create it first."
    exit 1
fi

echo "✅ Prerequisites check passed"

# Check if app already exists
APP_NAME="zid-integration-service"
EXISTING_APP=$(doctl apps list --format Name --no-header | grep "^${APP_NAME}$" || true)

if [ -n "$EXISTING_APP" ]; then
    echo "📱 App '$APP_NAME' already exists. Updating..."
    APP_ID=$(doctl apps list --format ID,Name --no-header | grep "$APP_NAME" | awk '{print $1}')
    doctl apps update "$APP_ID" --spec .do/app.yaml
    echo "✅ App updated successfully!"
else
    echo "🆕 Creating new app '$APP_NAME'..."
    doctl apps create --spec .do/app.yaml
    echo "✅ App created successfully!"
fi

echo ""
echo "🎉 Deployment initiated!"
echo ""
echo "Next steps:"
echo "1. 🔐 Set environment variables in DO dashboard:"
echo "   - ZID_CLIENT_ID (your Zid app client ID)"
echo "   - ZID_CLIENT_SECRET (your Zid app secret)"  
echo "   - SECRET_KEY (generate a secure key)"
echo ""
echo "2. 📝 Update your Zid app redirect URI to:"
echo "   https://your-app-name.ondigitalocean.app/auth/callback"
echo ""
echo "3. 🌐 Monitor deployment:"
echo "   doctl apps list"
echo "   doctl apps logs <APP_ID> --follow"
echo ""
echo "4. 🧪 Test your deployment:"
echo "   curl https://your-app-name.ondigitalocean.app/health"
echo ""
echo "📖 See DEPLOYMENT.md for detailed instructions"