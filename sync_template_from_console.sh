#!/bin/bash
# Script to sync console changes back to SAM template.yml
# This captures current AWS resource configurations and compares with template.yml

set -e

STACK_NAME="email-booking-parse-s3"
REGION="us-east-1"
OUTPUT_DIR="./sync_output"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "🔄 Syncing console changes to SAM template..."
echo "Stack: $STACK_NAME"
echo "Region: $REGION"
echo ""

# Create output directory
mkdir -p "$OUTPUT_DIR"

echo "📥 Step 1: Exporting current CloudFormation template..."
aws cloudformation get-template \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --query 'TemplateBody' \
    --output json > "$OUTPUT_DIR/deployed_template_${TIMESTAMP}.json" 2>/dev/null

echo "✅ Exported deployed template"
echo ""

echo "📥 Step 2: Getting Lambda function configurations..."

# Bookings API Lambda
echo "  - bookings-api-lambda"
aws lambda get-function-configuration \
    --function-name bookings-api-lambda \
    --region "$REGION" \
    --output json > "$OUTPUT_DIR/bookings_api_lambda_config.json" 2>/dev/null || echo "    ⚠️  Function not found"

# Email Parse Lambda
echo "  - email-parse-lambda"
aws lambda get-function-configuration \
    --function-name email-parse-lambda \
    --region "$REGION" \
    --output json > "$OUTPUT_DIR/email_parse_lambda_config.json" 2>/dev/null || echo "    ⚠️  Function not found"

echo ""

echo "📥 Step 3: Getting IAM role configurations..."

# Bookings API Role
ROLE_NAME_BOOKINGS=$(aws iam list-roles --query "Roles[?contains(RoleName, 'BookingsApiFunction')].RoleName" --output text | head -1)
if [ -n "$ROLE_NAME_BOOKINGS" ]; then
    echo "  - $ROLE_NAME_BOOKINGS"
    aws iam get-role --role-name "$ROLE_NAME_BOOKINGS" --output json > "$OUTPUT_DIR/bookings_api_role.json" 2>/dev/null
    
    # Get inline policies
    POLICIES=$(aws iam list-role-policies --role-name "$ROLE_NAME_BOOKINGS" --query 'PolicyNames' --output text 2>/dev/null)
    for policy in $POLICIES; do
        aws iam get-role-policy --role-name "$ROLE_NAME_BOOKINGS" --policy-name "$policy" --output json > "$OUTPUT_DIR/bookings_api_role_${policy}.json" 2>/dev/null
    done
    
    # Get attached policies
    aws iam list-attached-role-policies --role-name "$ROLE_NAME_BOOKINGS" --output json > "$OUTPUT_DIR/bookings_api_role_attached_policies.json" 2>/dev/null
fi

# Email Parse Role
ROLE_NAME_EMAIL=$(aws iam list-roles --query "Roles[?contains(RoleName, 'EmailParseFunction')].RoleName" --output text | head -1)
if [ -n "$ROLE_NAME_EMAIL" ]; then
    echo "  - $ROLE_NAME_EMAIL"
    aws iam get-role --role-name "$ROLE_NAME_EMAIL" --output json > "$OUTPUT_DIR/email_parse_role.json" 2>/dev/null
    
    # Get inline policies
    POLICIES=$(aws iam list-role-policies --role-name "$ROLE_NAME_EMAIL" --query 'PolicyNames' --output text 2>/dev/null)
    for policy in $POLICIES; do
        aws iam get-role-policy --role-name "$ROLE_NAME_EMAIL" --policy-name "$policy" --output json > "$OUTPUT_DIR/email_parse_role_${policy}.json" 2>/dev/null
    done
    
    # Get attached policies
    aws iam list-attached-role-policies --role-name "$ROLE_NAME_EMAIL" --output json > "$OUTPUT_DIR/email_parse_role_attached_policies.json" 2>/dev/null
fi

echo ""

echo "📥 Step 4: Getting API Gateway configurations..."

# Get HTTP APIs
aws apigatewayv2 get-apis --region "$REGION" --output json > "$OUTPUT_DIR/http_apis.json" 2>/dev/null

# Get REST APIs
aws apigateway get-rest-apis --region "$REGION" --output json > "$OUTPUT_DIR/rest_apis.json" 2>/dev/null

# Get API Gateway stages and integrations
if [ -f "$OUTPUT_DIR/http_apis.json" ]; then
    API_IDS=$(jq -r '.Items[]?.ApiId // empty' "$OUTPUT_DIR/http_apis.json" 2>/dev/null)
    for api_id in $API_IDS; do
        echo "  - HTTP API: $api_id"
        aws apigatewayv2 get-api --api-id "$api_id" --region "$REGION" --output json > "$OUTPUT_DIR/http_api_${api_id}_details.json" 2>/dev/null
        aws apigatewayv2 get-stages --api-id "$api_id" --region "$REGION" --output json > "$OUTPUT_DIR/http_api_${api_id}_stages.json" 2>/dev/null
        aws apigatewayv2 get-integrations --api-id "$api_id" --region "$REGION" --output json > "$OUTPUT_DIR/http_api_${api_id}_integrations.json" 2>/dev/null
    done
fi

echo ""

echo "📥 Step 5: Getting Lambda function URL configurations..."

aws lambda get-function-url-config --function-name bookings-api-lambda --region "$REGION" --output json > "$OUTPUT_DIR/bookings_api_function_url.json" 2>/dev/null || echo "  - No function URL for bookings-api-lambda"

echo ""

echo "📊 Step 6: Generating comparison report..."

cat > "$OUTPUT_DIR/comparison_report.md" << 'EOF'
# SAM Template Sync Report

This report compares the deployed AWS resources with your `template.yml`.

## Key Areas to Check

### 1. Lambda Functions
- **Environment Variables**: Check if any were added/modified in console
- **Timeout**: Compare with template
- **Memory**: Compare with template
- **Function URLs**: If created in console, need to add to template

### 2. IAM Roles and Policies
- **Inline Policies**: Check for additional policies added in console
- **Attached Managed Policies**: Check for AWS managed policies added
- **Permission Boundaries**: Check if added in console

### 3. API Gateway
- **CORS Configuration**: Often modified in console
- **Stages**: Check stage configurations
- **Custom Domains**: If added in console
- **API Keys/Usage Plans**: If added in console
- **Throttling/Rate Limiting**: Check if configured in console

### 4. Lambda Permissions
- **Resource-based Policies**: Check for additional invocations permissions
- **Event Source Mappings**: Check for triggers added in console

## Next Steps

1. Review the exported JSON files in this directory
2. Compare with your `template.yml`
3. Update `template.yml` to match console changes
4. Test with `sam build && sam deploy --no-execute-changeset` first
EOF

echo ""
echo "✅ Sync complete!"
echo ""
echo "📁 Output directory: $OUTPUT_DIR"
echo ""
echo "📋 Review the following files:"
echo "   - deployed_template_${TIMESTAMP}.json (Full deployed CloudFormation template)"
echo "   - *_lambda_config.json (Lambda function configurations)"
echo "   - *_role*.json (IAM role configurations)"
echo "   - http_api_*.json (API Gateway configurations)"
echo "   - comparison_report.md (This report)"
echo ""
echo "🔍 Common things to check:"
echo "   1. CORS configuration in API Gateway"
echo "   2. Additional IAM policies attached to roles"
echo "   3. Lambda environment variables"
echo "   4. Function URLs (if created manually)"
echo "   5. API Gateway stages and deployments"
echo "   6. Custom domains or API keys"
echo ""

