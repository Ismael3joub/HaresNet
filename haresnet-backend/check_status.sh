#!/bin/bash
# Quick start script for HaresNet with InfluxDB

echo "🚀 Starting HaresNet with InfluxDB..."
echo ""

# Check if containers are running
echo "📦 Checking container status..."
docker compose ps

echo ""
echo "✅ Services Status:"
echo ""

# Check backend
if docker compose ps | grep -q "haresnet-router.*Up"; then
    echo "  ✓ Backend (haresnet-router) - Running"
else
    echo "  ✗ Backend (haresnet-router) - Not running"
fi

# Check InfluxDB
if docker compose ps | grep -q "haresnet-influxdb.*Up"; then
    echo "  ✓ InfluxDB (haresnet-influxdb) - Running"
else
   echo "  ✗ InfluxDB (haresnet-influxdb) - Not running"
fi

echo ""
echo "📊 InfluxDB Connection:"
docker compose logs haresnet-backend 2>&1 | grep "InfluxDB.*Connected" | tail -1

echo ""
echo "🔧 Traffic Monitoring:"
docker compose logs haresnet-backend 2>&1 | grep "TrafficMonitor.*enabled" | tail -1

echo ""
echo "📈 Recent Traffic Activity:"
docker compose logs haresnet-backend 2>&1 | grep "TrafficMonitor\]" | grep -v "enabled\|InfluxDB" | tail -5

echo ""
echo "🌐 Access Points:"
echo "  - Backend API: http://localhost:5000"
echo "  - InfluxDB UI: http://localhost:8086"
echo "    Username: admin"
echo "    Password: haresnet_admin_password"
echo ""
echo "  - Frontend: http://localhost:5173 (if running npm run dev)"
echo ""

# Check if frontend is running
if lsof -Pi :5173 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo "  ✓ Frontend is running on port 5173"
else
    echo "  ⚠ Frontend not running. Start with:"
    echo "    cd /home/super/Desktop/guardian-angel && npm run dev"
fi

echo ""
echo "📋 Quick Commands:"
echo "  View logs:        docker compose logs -f"
echo "  Restart backend:  docker compose restart haresnet-backend"
echo "  Check InfluxDB:   docker exec haresnet-influxdb influx ping"
echo ""
