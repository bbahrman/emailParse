# Deployment Notes

## Current Status

The stack is currently in `DELETE_FAILED` or `UPDATE_FAILED` state due to Function URL CORS configuration issues.

## Solution

The FastAPI Lambda function (`bookings-api-lambda`) has been added to the template, but the Function URL needs to be created separately via AWS CLI due to CloudFormation validation issues with CORS configuration.

## Steps to Deploy

1. **Wait for stack to be in a stable state** (UPDATE_ROLLBACK_COMPLETE or similar), or manually clean up failed resources in AWS Console.

2. **Deploy the Lambda function** (without Function URL):
   ```bash
   sam build && sam deploy
   ```

3. **Create Function URL manually** using the provided script:
   ```bash
   ./create_function_url.sh
   ```

   Or manually via AWS CLI:
   ```bash
   aws lambda create-function-url-config \
       --function-name bookings-api-lambda \
       --auth-type NONE \
       --region us-east-1
   ```

4. **Get the Function URL**:
   ```bash
   aws lambda get-function-url-config \
       --function-name bookings-api-lambda \
       --region us-east-1 \
       --query 'FunctionUrl' \
       --output text
   ```

## Alternative: Use API Gateway

If Function URLs continue to have issues, consider using API Gateway HTTP API instead, which has better CORS support:

1. Add an `Events` section to the Lambda function in `template.yml`:
   ```yaml
   Events:
     Api:
       Type: HttpApi
       Properties:
         Path: /{proxy+}
         Method: ANY
   ```

2. This will automatically create an API Gateway HTTP API.

## Testing the API

Once deployed, test the endpoints:

```bash
# Get booking by ID
curl https://<function-url>/bookings/RL37906759

# Get bookings by date range
curl "https://<function-url>/bookings/?start_date=2025-11-17&end_date=2025-11-20"

# View API docs
curl https://<function-url>/docs
```

