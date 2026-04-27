#!/bin/bash
# HaresNet Backend Setup Script

echo "========================================="
echo "HaresNet Backend Setup"
echo "========================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
  echo "⚠️  Warning: This script may need root privileges for network operations"
fi

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "✗ Docker is not installed"
    echo "  Please install Docker first: https://docs.docker.com/engine/install/"
    exit 1
fi
echo "✓ Docker is installed"

# Check Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "✗ Docker Compose is not installed"
    echo "  Please install Docker Compose first"
    exit 1
fi
echo "✓ Docker Compose is installed"

# List network interfaces
echo ""
echo "Available Network Interfaces:"
echo "-------------------------------------"
ip link show | grep -E '^[0-9]+:' | awk '{print $2}' | sed 's/://'
echo ""

# Prompt for WAN interface
read -p "Enter WAN interface (e.g., eth0): " wan_interface
if [ -z "$wan_interface" ]; then
    echo "✗ WAN interface is required"
    exit 1
fi

# Prompt for LAN interface
read -p "Enter LAN interface (e.g., wlan0): " lan_interface
if [ -z "$lan_interface" ]; then
    echo "✗ LAN interface is required"
    exit 1
fi

# Check if LAN interface supports AP mode
echo ""
echo "Checking if $lan_interface supports AP mode..."
if iw list &> /dev/null; then
    if iw dev $lan_interface info &> /dev/null; then
        if iw list | grep -A 8 "Supported interface modes" | grep -q "AP"; then
            echo "✓ AP mode is supported"
        else
            echo "⚠️  Warning: AP mode may not be supported on this interface"
            read -p "Continue anyway? (y/n): " continue
            if [ "$continue" != "y" ]; then
                exit 1
            fi
        fi
    else
        echo "⚠️  Warning: Cannot check interface $lan_interface"
    fi
else
    echo "⚠️  iw tool not found, cannot verify AP mode support"
fi

# Update docker-compose.yml
echo ""
echo "Updating docker-compose.yml..."
sed -i "s/WAN_INTERFACE=.*/WAN_INTERFACE=$wan_interface/" docker-compose.yml
sed -i "s/LAN_INTERFACE=.*/LAN_INTERFACE=$lan_interface/" docker-compose.yml
echo "✓ Configuration updated"

# Generate random secrets
echo ""
echo "Generating random secrets..."
secret_key=$(openssl rand -hex 32)
jwt_secret=$(openssl rand -hex 32)

sed -i "s/SECRET_KEY=.*/SECRET_KEY=$secret_key/" docker-compose.yml
sed -i "s/JWT_SECRET_KEY=.*/JWT_SECRET_KEY=$jwt_secret/" docker-compose.yml
echo "✓ Secrets generated"

# Build and start
echo ""
read -p "Build and start the container now? (y/n): " build
if [ "$build" = "y" ]; then
    echo "Building Docker image..."
    docker-compose build
    
    echo ""
    echo "Starting container..."
    docker-compose up -d
    
    echo ""
    echo "========================================="
    echo "✓ HaresNet Backend is running!"
    echo "========================================="
    echo ""
    echo "API URL: http://localhost:5000/api"
    echo "Default credentials:"
    echo "  Username: admin"
    echo "  Password: haresnet2024"
    echo ""
    echo "View logs: docker-compose logs -f"
    echo "Stop: docker-compose down"
    echo ""
    echo "⚠️  IMPORTANT: Change the default password after first login!"
else
    echo ""
    echo "Configuration saved. To start later, run:"
    echo "  docker-compose up -d"
fi
