#!/bin/bash
# Enable DNS query logging in dnsmasq (for Docker container)

echo "🔧 Enabling DNS Query Logging..."

# Check if dnsmasq config has logging enabled
if ! grep -q "^log-queries" /etc/dnsmasq.conf; then
    echo "Enabling log-queries in dnsmasq.conf..."
    
    # Create log file
    touch /var/log/dnsmasq.log
    chmod 644 /var/log/dnsmasq.log
    
    # Add logging config to dnsmasq.conf
    cat >> /etc/dnsmasq.conf << EOF

# DNS Query Logging (added by setup script)
log-queries
log-facility=/var/log/dnsmasq.log
log-async=20
EOF
    
    echo "✓ Configuration updated"
    
    # Restart dnsmasq
    echo "🔄 Restarting dnsmasq..."
    pkill -f "^dnsmasq" || true
    sleep 1
    dnsmasq --conf-file=/etc/dnsmasq.conf &
    sleep 2
    
    if pgrep -x "dnsmasq" > /dev/null; then
        echo "✓ dnsmasq restarted successfully"
    else
        echo "✗ Failed to restart dnsmasq"
        exit 1
    fi
else
    echo "✓ DNS logging already enabled"
fi

echo ""
echo "📊 DNS Log file location: /var/log/dnsmasq.log"
echo "✓ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Make DNS queries from your devices"
echo "2. Check logs with: python3 check_dns_logs.py --logs"
echo "3. View stats with: python3 check_dns_logs.py --stats"
