#!/bin/bash
# Package project for AWS Lambda deployment
# Creates a zip file with source code and dependencies

set -e

PACKAGE_NAME="email-parse-deployment"
BUILD_DIR=".aws-package"
ZIP_FILE="${PACKAGE_NAME}.zip"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "📦 Packaging project for AWS deployment..."
echo ""

# Clean up any previous build
rm -rf "$BUILD_DIR"
rm -f "${PACKAGE_NAME}"*.zip

# Create build directory
mkdir -p "$BUILD_DIR"

echo "📋 Step 1: Copying source code..."

# Copy application code
cp -r app "$BUILD_DIR/"

# Copy configuration files
cp template.yml "$BUILD_DIR/" 2>/dev/null || true
cp samconfig.toml "$BUILD_DIR/" 2>/dev/null || true
cp requirements.txt "$BUILD_DIR/"
cp pyproject.toml "$BUILD_DIR/" 2>/dev/null || true

# Copy Lambda handler entry points
cp run_lambda_handler.py "$BUILD_DIR/" 2>/dev/null || true

echo "✅ Source code copied"
echo ""

echo "📋 Step 2: Installing dependencies..."

# Install dependencies into build directory
python3 -m pip install -r requirements.txt -t "$BUILD_DIR" --upgrade --quiet

echo "✅ Dependencies installed"
echo ""

echo "📋 Step 3: Cleaning up unnecessary files..."

# Remove unnecessary files from dependencies
find "$BUILD_DIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "$BUILD_DIR" -type f -name "*.pyc" -delete 2>/dev/null || true
find "$BUILD_DIR" -type f -name "*.pyo" -delete 2>/dev/null || true
find "$BUILD_DIR" -type d -name "*.dist-info" -exec rm -rf {} + 2>/dev/null || true
find "$BUILD_DIR" -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true

# Remove test directories and files from dependencies
find "$BUILD_DIR" -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true
find "$BUILD_DIR" -type d -name "test" -exec rm -rf {} + 2>/dev/null || true
find "$BUILD_DIR" -type d -name "__tests__" -exec rm -rf {} + 2>/dev/null || true

# Remove documentation
find "$BUILD_DIR" -type d -name "docs" -exec rm -rf {} + 2>/dev/null || true
find "$BUILD_DIR" -type f -name "*.md" -delete 2>/dev/null || true
find "$BUILD_DIR" -type f -name "*.txt" -not -name "requirements.txt" -delete 2>/dev/null || true

# Remove unnecessary binary files (keep only .so files needed for runtime)
find "$BUILD_DIR" -type f -name "*.exe" -delete 2>/dev/null || true

echo "✅ Cleanup complete"
echo ""

echo "📋 Step 4: Creating zip archive..."

# Change to build directory to create relative paths in zip
cd "$BUILD_DIR"
zip -r "../${PACKAGE_NAME}_${TIMESTAMP}.zip" . -q
cd ..

# Also create a symlink/latest version
cp "${PACKAGE_NAME}_${TIMESTAMP}.zip" "$ZIP_FILE"

echo "✅ Zip file created: ${PACKAGE_NAME}_${TIMESTAMP}.zip"
echo "✅ Latest version: $ZIP_FILE"
echo ""

echo "📊 Package summary:"
echo "   Size: $(du -h "$ZIP_FILE" | cut -f1)"
echo "   Files: $(unzip -l "$ZIP_FILE" | tail -1 | awk '{print $2}')"
echo ""

echo "📋 Step 5: Validating package..."

# Check for required files
if [ ! -d "$BUILD_DIR/app" ]; then
    echo "⚠️  Warning: app/ directory not found in package"
fi

if [ ! -f "$BUILD_DIR/requirements.txt" ]; then
    echo "⚠️  Warning: requirements.txt not found in package"
fi

# Check zip file size (Lambda limit is 50MB unzipped, 250MB unzipped for container)
ZIP_SIZE=$(stat -f%z "$ZIP_FILE" 2>/dev/null || stat -c%s "$ZIP_FILE" 2>/dev/null)
ZIP_SIZE_MB=$((ZIP_SIZE / 1024 / 1024))

if [ $ZIP_SIZE_MB -gt 50 ]; then
    echo "⚠️  Warning: Package size is ${ZIP_SIZE_MB}MB (Lambda limit: 50MB compressed)"
    echo "   Consider using Lambda layers or container images for larger packages"
else
    echo "✅ Package size: ${ZIP_SIZE_MB}MB (within Lambda limits)"
fi

echo ""
echo "🎉 Packaging complete!"
echo ""
echo "📤 Ready to upload:"
echo "   • Full path: $(pwd)/$ZIP_FILE"
echo "   • Timestamped: $(pwd)/${PACKAGE_NAME}_${TIMESTAMP}.zip"
echo ""
echo "🚀 Upload options:"
echo "   1. AWS Console: Lambda > Functions > Upload from > .zip file"
echo "   2. AWS CLI: aws lambda update-function-code --function-name <name> --zip-file fileb://$ZIP_FILE"
echo "   3. SAM Deploy: Use ./deploy.sh (SAM handles packaging automatically)"
echo ""
echo "🧹 To clean up build files: rm -rf $BUILD_DIR"

