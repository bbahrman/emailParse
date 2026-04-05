#!/bin/bash
# SAM deployment script
# Deploys to personal AWS account (profile: default)
# Requires environment variable: TRAVEL_ANTHROPIC_API_KEY

set -e

if [ -z "$TRAVEL_ANTHROPIC_API_KEY" ]; then
    echo "Error: TRAVEL_ANTHROPIC_API_KEY environment variable is not set"
    exit 1
fi

# Verify we're deploying to the correct account
ACCOUNT_ID=$(aws sts get-caller-identity --profile default --query Account --output text 2>/dev/null)
if [ "$ACCOUNT_ID" != "398501876458" ]; then
    echo "Error: Expected personal account 398501876458 but got $ACCOUNT_ID"
    exit 1
fi

echo "Building SAM application..."
sam build

echo "Cleaning build artifacts (removing frontend/plugin from Lambda packages)..."
rm -rf .aws-sam/build/EmailParseFunction/web \
       .aws-sam/build/EmailParseFunction/obsidian-travel-sync \
       .aws-sam/build/BookingsApiFunction/web \
       .aws-sam/build/BookingsApiFunction/obsidian-travel-sync

echo "Deploying stack to account $ACCOUNT_ID..."
sam deploy \
    --config-env default \
    --no-fail-on-empty-changeset \
    --resolve-s3 \
    --profile default \
    --parameter-overrides \
        "AnthropicApiKey=$TRAVEL_ANTHROPIC_API_KEY"

echo "Deployment complete!"
