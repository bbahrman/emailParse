#!/bin/bash
# Package source code only (for SAM deployments or Lambda layers)
# This creates a lightweight zip with just source code, no dependencies

set -e

PACKAGE_NAME="email-parse-source"
BUILD_DIR=".aws-source-package"
ZIP_FILE="${PACKAGE_NAME}.zip"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "📦 Packaging source code only (no dependencies)..."
echo ""

# Clean up any previous build
rm -rf "$BUILD_DIR"
rm -f "${PACKAGE_NAME}"*.zip

# Create build directory
mkdir -p "$BUILD_DIR"

echo "📋 Copying source files..."

# Copy application code
cp -r app "$BUILD_DIR/"

# Copy configuration files
cp template.yml "$BUILD_DIR/" 2>/dev/null || true
cp samconfig.toml "$BUILD_DIR/" 2>/dev/null || true
cp requirements.txt "$BUILD_DIR/"
cp pyproject.toml "$BUILD_DIR/" 2>/dev/null || true

# Copy Lambda handler entry points
cp run_lambda_handler.py "$BUILD_DIR/" 2>/dev/null || true

echo "✅ Source files copied"
echo ""

echo "📋 Cleaning up..."

# Remove Python cache files
find "$BUILD_DIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "$BUILD_DIR" -type f -name "*.pyc" -delete 2>/dev/null || true
find "$BUILD_DIR" -type f -name "*.pyo" -delete 2>/dev/null || true

echo "✅ Cleanup complete"
echo ""

echo "📋 Creating zip archive..."

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

echo "🎉 Source-only packaging complete!"
echo ""
echo "📤 Ready to upload:"
echo "   • Full path: $(pwd)/$ZIP_FILE"
echo ""
echo "💡 Note: This package does NOT include dependencies."
echo "   Use this for SAM deployments (dependencies are managed separately)"
echo "   or for Lambda layers."

