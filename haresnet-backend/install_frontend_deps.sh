#!/bin/bash
set -e

FRONTEND_DIR="/home/super/Desktop/guardian-angel"

if [ ! -d "$FRONTEND_DIR" ]; then
    echo "Error: Frontend directory not found at $FRONTEND_DIR"
    exit 1
fi

echo "Installing socket.io-client in $FRONTEND_DIR..."
cd "$FRONTEND_DIR"
npm install socket.io-client

echo "============================================"
echo "✅ Dependency installed successfully!"
echo "Please restart your frontend server (Vite) to pick up the changes."
echo "============================================"
