# Syncing Console Changes to SAM Template

When you make changes to AWS resources via the AWS Console, those changes exist only in your deployed infrastructure and not in your `template.yml`. This guide helps you sync those changes back to your template.

## Quick Start

### Step 1: Export Current Configuration

Run the sync script to capture all current resource configurations:

```bash
./sync_template_from_console.sh
```

This will:
- Export the current CloudFormation template
- Capture Lambda function configurations
- Export IAM role policies
- Export API Gateway configurations
- Generate a comparison report

All output is saved to `./sync_output/` directory.

### Step 2: Analyze Differences

Run the analysis script to get suggestions:

```bash
./update_template_from_sync.py
```

This will analyze the exported configurations and suggest what needs to be updated in `template.yml`.

### Step 3: Update template.yml

Review the suggestions and update your `template.yml` accordingly.

### Step 4: Test Before Deploying

Test your changes without deploying:

```bash
sam build && sam deploy --no-execute-changeset
```

### Step 5: Deploy

Once verified, deploy the updated template:

```bash
./deploy.sh
```

## Common Console Changes to Sync

### 1. API Gateway CORS Configuration

If you added CORS in the console, add to `template.yml`:

```yaml
ServerlessHttpApi:
  Type: AWS::ApiGatewayV2::Api
  Properties:
    CorsConfiguration:
      AllowOrigins:
        - "*"
      AllowMethods:
        - GET
        - POST
        - OPTIONS
      AllowHeaders:
        - "*"
```

### 2. Additional IAM Policies

If you attached managed policies in console, add to Lambda function:

```yaml
BookingsApiFunction:
  Type: AWS::Serverless::Function
  Properties:
    # ... existing config ...
    ManagedPolicyArns:
      - arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess
```

Or add inline policies to the `Policies` section.

### 3. Lambda Environment Variables

If you added environment variables in console:

```yaml
BookingsApiFunction:
  Type: AWS::Serverless::Function
  Properties:
    Environment:
      Variables:
        EXISTING_VAR: value
        NEW_VAR_FROM_CONSOLE: new_value  # Add this
```

### 4. Lambda Function URLs

If you created a Function URL in console, add to template:

```yaml
BookingsApiFunction:
  Type: AWS::Serverless::Function
  Properties:
    # ... existing config ...
    FunctionUrlConfig:
      AuthType: NONE  # or AWS_IAM
      Cors:
        AllowOrigins:
          - "*"
```

### 5. API Gateway Stage Settings

If you modified stage settings:

```yaml
ServerlessHttpApiApiGatewayDefaultStage:
  Type: AWS::ApiGatewayV2::Stage
  Properties:
    # ... existing config ...
    DefaultRouteSettings:
      ThrottlingBurstLimit: 5000
      ThrottlingRateLimit: 2000
      DetailedMetricsEnabled: true
```

### 6. API Gateway Custom Domain

If you added a custom domain:

```yaml
ApiDomainName:
  Type: AWS::ApiGatewayV2::DomainName
  Properties:
    DomainName: api.example.com
    DomainNameConfigurations:
      - CertificateArn: arn:aws:acm:...
        EndpointType: REGIONAL

ApiDomainMapping:
  Type: AWS::ApiGatewayV2::ApiMapping
  Properties:
    ApiId: !Ref ServerlessHttpApi
    DomainName: !Ref ApiDomainName
    Stage: !Ref ServerlessHttpApiApiGatewayDefaultStage
```

## Verification Steps

After updating `template.yml`:

1. **Validate template syntax:**
   ```bash
   sam validate
   ```

2. **Build without deploying:**
   ```bash
   sam build
   ```

3. **Preview changes:**
   ```bash
   sam deploy --no-execute-changeset
   ```

4. **Review the changeset** to ensure only expected changes will be made

5. **Deploy when ready:**
   ```bash
   ./deploy.sh
   ```

## Important Notes

⚠️ **CloudFormation Drift**: If you make console changes after syncing, they will cause "drift" - differences between your template and actual resources. Always sync console changes back to your template.

⚠️ **Resource Replacement**: Some changes in the console might require resource replacement when synced back. Review the CloudFormation changeset carefully before deploying.

⚠️ **Manual Resources**: Resources created manually (outside CloudFormation) won't appear in the deployed template. You may need to import them or recreate them via template.

## Troubleshooting

### "Stack is in UPDATE_ROLLBACK_COMPLETE"

If your stack failed to update, you may need to continue the rollback:

```bash
aws cloudformation continue-update-rollback \
    --stack-name email-booking-parse-s3 \
    --region us-east-1
```

### "Resource already exists"

If you get conflicts, you may need to:
1. Use different resource names in template
2. Import existing resources into CloudFormation
3. Delete and recreate resources (⚠️ data loss risk)

### Changes not reflecting

Ensure:
- You're using the correct stack name
- You're in the correct region
- You've saved `template.yml`
- You've run `sam build` before deploy

