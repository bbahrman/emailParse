# Packaging for AWS Deployment

This project includes scripts to package your code for AWS Lambda deployment.

## Quick Start

### Option 1: Full Package (with dependencies)
For direct Lambda function upload or when dependencies aren't in a layer:

```bash
./package_for_aws.sh
```

This creates `email-parse-deployment.zip` with:
- Your source code (`app/`)
- All Python dependencies installed
- Configuration files
- Ready for direct Lambda upload

### Option 2: Source Only
For SAM deployments or Lambda layers:

```bash
./package_source_only.sh
```

This creates `email-parse-source.zip` with:
- Your source code only
- No dependencies (SAM installs them separately)
- Configuration files

## Package Contents

### Full Package Includes:
- ✅ Application code (`app/`)
- ✅ Python dependencies (from `requirements.txt`)
- ✅ Configuration files (`template.yml`, `samconfig.toml`)
- ✅ Requirements file
- ❌ Tests (excluded)
- ❌ Virtual environment (excluded)
- ❌ Cache files (excluded)
- ❌ Documentation (excluded)

### Source Package Includes:
- ✅ Application code (`app/`)
- ✅ Configuration files
- ✅ Requirements file
- ❌ Dependencies (not included - installed separately)
- ❌ Tests (excluded)
- ❌ Virtual environment (excluded)

## Upload Options

### 1. AWS Console Upload
1. Go to AWS Lambda Console
2. Select your function
3. Upload > Upload from > .zip file
4. Select the generated zip file

### 2. AWS CLI Upload
```bash
aws lambda update-function-code \
    --function-name bookings-api-lambda \
    --zip-file fileb://email-parse-deployment.zip \
    --region us-east-1
```

### 3. SAM Deploy (Recommended)
SAM automatically packages your code:
```bash
sam build
sam deploy
```

Or use the deployment script:
```bash
./deploy.sh
```

## File Size Limits

- **Lambda ZIP**: 50 MB (compressed)
- **Lambda Unzipped**: 250 MB (uncompressed)
- **Lambda Container**: 10 GB

If your package exceeds 50 MB:
1. Use Lambda Layers for dependencies
2. Use container images instead
3. Optimize dependencies (remove unused packages)

## Verification

After packaging, check the zip contents:

```bash
unzip -l email-parse-deployment.zip | less
```

Or check the package size:

```bash
ls -lh email-parse-deployment.zip
```

## Troubleshooting

### Package too large
- Remove unnecessary dependencies
- Use Lambda Layers
- Switch to container images

### Missing dependencies
- Ensure `requirements.txt` is up to date
- Run `pip freeze > requirements.txt` to capture current environment
- Check that all dependencies are in requirements.txt

### Import errors after upload
- Ensure all dependencies are in the zip
- Check that handler paths are correct
- Verify Python runtime version matches locally

## Clean Up

Remove build directories:

```bash
rm -rf .aws-package .aws-source-package
```

Remove generated zip files:

```bash
rm -f email-parse-*.zip
```

