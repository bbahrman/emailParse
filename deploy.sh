#!/bin/bash
# SAM deployment script for AWS Toolkit
# Updates existing stack resources using configuration from samconfig.toml

set -e  # Exit on error

echo "🚀 Starting SAM deployment..."
echo ""

# Step 1: Build the SAM application
echo "📦 Building SAM application..."
sam build

if [ $? -ne 0 ]; then
    echo "❌ SAM build failed!"
    exit 1
fi

echo "✅ Build successful!"
echo ""

# Step 2: Deploy using samconfig.toml configuration
# AWS Toolkit reads samconfig.toml automatically when using --config-env default
echo "🚀 Deploying stack (using samconfig.toml)..."
sam deploy --config-env default --no-fail-on-empty-changeset

if [ $? -ne 0 ]; then
    echo "❌ Deployment failed!"
    exit 1
fi

echo ""
echo "✅ Deployment complete!"

