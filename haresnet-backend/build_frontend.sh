#!/bin/bash

# Build Frontend Script for HaresNet
# This script builds the React frontend and places it in the Flask static directory

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="$SCRIPT_DIR/../guardian-angel"
BACKEND_STATIC_DIR="$SCRIPT_DIR/app/static/dist"

echo "🔨 Building HaresNet Frontend..."

# Check if frontend directory exists
if [ ! -d "$FRONTEND_DIR" ]; then
    echo "❌ Error: Frontend directory not found at $FRONTEND_DIR"
    exit 1
fi

# Navigate to frontend directory
cd "$FRONTEND_DIR"

# Install dependencies if node_modules doesn't exist
if [ ! -d "node_modules" ]; then
    echo "📦 Installing frontend dependencies..."
    npm install
fi

# Build the frontend
echo "🏗️  Building frontend..."
npm run build

# Verify build was successful
if [ -d "$BACKEND_STATIC_DIR" ] && [ -f "$BACKEND_STATIC_DIR/index.html" ]; then
    echo "✅ Frontend built successfully!"
    echo "📁 Built files location: $BACKEND_STATIC_DIR"
    echo ""
    echo "You can now access the interface at:"
    echo "  - http://localhost (or http://localhost:80)"
    echo "  - http://<your-ip> (from your network, e.g., http://192.168.10.1)"
else
    echo "❌ Error: Build failed or files not found in expected location"
    exit 1
fi
