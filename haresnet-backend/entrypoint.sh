#!/bin/bash
# HaresNet Docker Entrypoint
# Automatically detects interfaces and starts all services

set -e

echo "========================================="
echo "HaresNet Router Starting..."
echo "========================================="

# Enable IP forwarding
echo "Enabling IP forwarding..."
echo 1 > /proc/sys/net/ipv4/ip_forward
sysctl -w net.ipv4.ip_forward=1 > /dev/null 2>&1

# Detect Wi-Fi interface
echo "Detecting Wi-Fi interface..."
WIFI_IFACE=$(iw dev 2>/dev/null | awk '$1=="Interface"{print $2}' | grep -E '^(wlx|wlan)' | head -n 1)

if [ -z "$WIFI_IFACE" ]; then
    echo "⚠️  No Wi-Fi interface found!"
    echo "   Using LAN_INTERFACE from environment: ${LAN_INTERFACE}"
    WIFI_IFACE=${LAN_INTERFACE}
else
    echo "✓ Detected Wi-Fi interface: $WIFI_IFACE"
    export LAN_INTERFACE=$WIFI_IFACE
fi

# Detect WAN interface
echo "Detecting WAN interface..."
WAN_IFACE=$(ip route 2>/dev/null | awk '/default/ {print $5; exit}')

if [ -z "$WAN_IFACE" ]; then
    echo "⚠️  No default route found!"
    echo "   Using WAN_INTERFACE from environment: ${WAN_INTERFACE}"
    WAN_IFACE=${WAN_INTERFACE}
else
    echo "✓ Detected WAN interface: $WAN_IFACE"
    export WAN_INTERFACE=$WAN_IFACE
fi

echo ""
echo "Network Configuration:"
echo "  LAN (Wi-Fi): $WIFI_IFACE"
echo "  WAN (Internet): $WAN_IFACE"
echo "  LAN IP: ${LAN_IP}"
echo ""

# Apply configuration from database (generates dnsmasq.conf, hostapd.conf, network config)
echo "Applying configuration from database..."
export PYTHONPATH=$PYTHONPATH:.
python3 scripts/apply_router_config.py || echo "⚠️  Failed to apply configuration from database"

# Ensure dnsmasq auxiliary files exist
echo "Ensuring DNS filter config files exist..."
mkdir -p /etc/dnsmasq.d
touch /etc/dnsmasq.d/blocklist.conf
touch /etc/dnsmasq.d/allowlist.conf

# Ensure dnsmasq.conf has port=5353 (DNS Proxy needs port 53)
# The Python DnsmasqManager should handle this, but as a safety net:
if ! grep -q "^port=5353" /etc/dnsmasq.conf 2>/dev/null; then
    echo "Patching dnsmasq.conf to use port 5353..."
    # Add port=5353 after bind-interfaces if missing
    if grep -q "bind-interfaces" /etc/dnsmasq.conf; then
        sed -i '/^bind-interfaces/a port=5353' /etc/dnsmasq.conf
    else
        echo "port=5353" >> /etc/dnsmasq.conf
    fi
fi

# Ensure dnsmasq.conf references blocklist/allowlist
if ! grep -q "blocklist.conf" /etc/dnsmasq.conf 2>/dev/null; then
    echo "Adding blocklist/allowlist includes to dnsmasq.conf..."
    echo "" >> /etc/dnsmasq.conf
    echo "# DNS Filter includes" >> /etc/dnsmasq.conf
    echo "conf-file=/etc/dnsmasq.d/blocklist.conf" >> /etc/dnsmasq.conf
    echo "conf-file=/etc/dnsmasq.d/allowlist.conf" >> /etc/dnsmasq.conf
fi

# Start dnsmasq (it will use port=5353 from config)
echo "Starting DHCP/DNS server (dnsmasq on port 5353)..."
dnsmasq --conf-file=/etc/dnsmasq.conf 2>&1 | tee -a /var/log/dnsmasq.log &
sleep 2
echo "✓ DHCP/DNS started"

# Configure basic NAT using nftables (minimal - just masquerade for internet)
# The full firewall rules (DNS hijacking, child safety, etc) are handled by run.py
if [ -n "$WAN_INTERFACE" ]; then
    echo "Configuring basic NAT (internet sharing)..."
    
    nft flush ruleset 2>/dev/null || true
    
    # Create table and basic NAT masquerade (just enough for internet)
    nft add table inet haresnet
    nft add chain inet haresnet postrouting { type nat hook postrouting priority 100\; }
    nft add rule inet haresnet postrouting oifname "$WAN_INTERFACE" masquerade
    
    echo "✓ Basic NAT configured ($WAN_INTERFACE)"
fi

# Start hostapd
echo "Starting Wi-Fi Access Point..."
hostapd -B /etc/hostapd/hostapd.conf 2>&1 | tee -a /var/log/hostapd.log
sleep 3

if pgrep -x "hostapd" > /dev/null; then
    echo "✓ Wi-Fi AP started successfully!"
else
    echo "⚠️  hostapd may not have started - check /var/log/hostapd.log"
fi

# Run migration for Service domain
echo "Checking for database migrations..."
python3 migrate_service_domain.py || echo "⚠️  Migration script failed or not needed"

# Wait for LAN IP to be assigned
echo "Waiting for LAN IP ${LAN_IP} to be assigned..."
timeout=30
while [ $timeout -gt 0 ]; do
    if ip addr show qt 192.168.10.1 >/dev/null 2>&1; then
        echo "✓ LAN IP assigned"
        break
    fi
    if ip addr | grep -q "${LAN_IP}"; then
         echo "✓ LAN IP found on host"
         break
    fi
    sleep 1
    timeout=$((timeout - 1))
done

echo ""
echo "========================================="
echo "✓ Network Services Running"
echo "========================================="
echo ""
echo "Starting Flask API on port ${PORT:-80}..."
echo ""

# Start Flask application (this handles full firewall init, DNS proxy, etc)
exec python3 run.py
