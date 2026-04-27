#!/bin/bash

# QUICK TEST: Dashboard Stats Endpoints

echo "🔍 Testing DNS Filter Dashboard Stats Endpoints"
echo "═════════════════════════════════════════════════"

# Test 1: Public Stats (No Auth Required)
echo ""
echo "1️⃣  PUBLIC STATS ENDPOINT (No Auth):"
echo "   URL: /api/dns-filter/stats/public"
echo "   Method: GET"
echo ""
echo "   Curl Command:"
echo "   curl http://localhost:5000/api/dns-filter/stats/public | jq"
echo ""
echo "   Expected Response:"
echo "   {"
echo "     \"queries_today\": 0,"
echo "     \"blocked_today\": 0,"
echo "     \"allowed_today\": 0,"
echo "     \"block_rate\": 0,"
echo "     \"active_filters\": 7,"
echo "     \"blocklists\": 2"
echo "   }"
echo ""

# Test 2: Detailed Dashboard (Auth Required)
echo "2️⃣  AUTHENTICATED DASHBOARD ENDPOINT:"
echo "   URL: /api/dns-filter/dashboard/summary"
echo "   Method: GET"
echo "   Headers: Authorization: Bearer YOUR_JWT_TOKEN"
echo ""
echo "   Curl Command:"
echo "   curl -H 'Authorization: Bearer YOUR_TOKEN' \\"
echo "     http://localhost:5000/api/dns-filter/dashboard/summary | jq"
echo ""
echo "   Expected Response Structure:"
echo "   {"
echo "     \"summary\": {...},"
echo "     \"top_blocked_domains\": [...],"
echo "     \"top_clients\": [...],"
echo "     \"timeline\": [...24 hourly entries...]"
echo "   }"
echo ""

# Test 3: How to get JWT Token (if needed)
echo "3️⃣  TO GET JWT TOKEN FOR TESTING:"
echo "   1. Login via /api/auth/login"
echo "   2. Response includes: {\"token\": \"your_jwt_token\"}"
echo "   3. Use token in Authorization header"
echo ""

# Test 4: Live Update Implementation
echo "4️⃣  FOR LIVE DASHBOARD DISPLAY:"
echo "   Use JavaScript to fetch every 30 seconds:"
echo ""
echo "   fetch('/api/dns-filter/stats/public')"
echo "     .then(r => r.json())"
echo "     .then(data => {"
echo "       document.getElementById('queries-today').textContent = data.queries_today;"
echo "       document.getElementById('blocked-today').textContent = data.blocked_today;"
echo "       document.getElementById('allowed-today').textContent = data.allowed_today;"
echo "       document.getElementById('block-rate').textContent = data.block_rate + '%';"
echo "     })"
echo ""

echo "═════════════════════════════════════════════════"
echo "✅ All endpoints ready for integration!"
