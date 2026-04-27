#!/bin/bash
# HaresNet Wi-Fi Start Script
# This script configures and starts the Wi-Fi Access Point

echo "========================================="
echo "HaresNet Wi-Fi Configuration"
echo "========================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
  echo "⚠️  This script must be run as root"
  echo "   Run: sudo ./start-wifi.sh"
  exit 1
fi

# Detect Wi-Fi interface
echo "Detecting Wi-Fi interface..."
WIFI_IFACE=$(iw dev | awk '$1=="Interface"{print $2}' | head -n 1)

if [ -z "$WIFI_IFACE" ]; then
    echo "✗ No Wi-Fi interface found"
    echo "  Please ensure a Wi-Fi adapter is connected"
    exit 1
fi

echo "✓ Found Wi-Fi interface: $WIFI_IFACE"

# Detect WAN interface
echo "Detecting WAN (internet) interface..."
WAN_IFACE=$(ip route | awk '/default/ {print $5; exit}')

if [ -z "$WAN_IFACE" ]; then
    echo "⚠️  No default route found - no internet connection"
    echo "  Wi-Fi AP will start but won't have internet access"
else
    echo "✓ Found WAN interface: $WAN_IFACE"
fi

# Check if interface supports AP mode
echo ""
echo "Checking AP mode support..."
if iw list | grep -A 8 "Supported interface modes" | grep -q "AP"; then
    echo "✓ AP mode is supported"
else
    echo "⚠️  Warning: AP mode may not be supported"
    read -p "Continue anyway? (y/n): " continue
    if [ "$continue" != "y" ]; then
        exit 1
    fi
fi

# Get Wi-Fi configuration
echo ""
echo "Wi-Fi Configuration"
echo "-------------------"
read -p "SSID (network name) [HaresNet]: " ssid
ssid=${ssid:-HaresNet}

read -s -p "Password (min 8 characters): " password
echo ""

if [ ${#password} -lt 8 ]; then
    echo "✗ Password must be at least 8 characters"
    exit 1
fi

read -p "Channel (1-13) [6]: " channel
channel=${channel:-6}

# Create hostapd configuration
echo ""
echo "Creating hostapd configuration..."

cat > /etc/hostapd/hostapd.conf <<EOF
# HaresNet hostapd configuration
interface=$WIFI_IFACE
driver=nl80211
ssid=$ssid
hw_mode=g
channel=$channel
wmm_enabled=1
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=2
wpa_passphrase=$password
wpa_key_mgmt=WPA-PSK
rsn_pairwise=CCMP
EOF

echo "✓ Configuration created"

# Configure network interface
echo ""
echo "Configuring network interface..."
ip addr flush dev $WIFI_IFACE
ip addr add 192.168.10.1/24 dev $WIFI_IFACE
ip link set $WIFI_IFACE up

echo "✓ Interface configured (192.168.10.1)"

# Create dnsmasq configuration
echo ""
echo "Configuring DHCP/DNS..."

cat > /etc/dnsmasq.d/haresnet.conf <<EOF
# HaresNet dnsmasq configuration
interface=$WIFI_IFACE
dhcp-range=192.168.10.100,192.168.10.200,12h
dhcp-option=3,192.168.10.1
dhcp-option=6,192.168.10.1
domain=haresnet.local
no-resolv
server=8.8.8.8
server=8.8.4.4
EOF

echo "✓ DHCP/DNS configured"

# Enable IP forwarding
echo ""
echo "Enabling IP forwarding..."
echo 1 > /proc/sys/net/ipv4/ip_forward
sysctl -w net.ipv4.ip_forward=1 > /dev/null 2>&1

echo "✓ IP forwarding enabled"

# Configure NAT
if [ -n "$WAN_IFACE" ]; then
    echo ""
    echo "Configuring NAT (internet sharing)..."
    
    # Clear existing rules
    iptables -t nat -F
    iptables -F FORWARD
    
    # Add NAT rule
    iptables -t nat -A POSTROUTING -o $WAN_IFACE -j MASQUERADE
    iptables -A FORWARD -i $WIFI_IFACE -o $WAN_IFACE -j ACCEPT
    iptables -A FORWARD -i $WAN_IFACE -o $WIFI_IFACE -m state --state RELATED,ESTABLISHED -j ACCEPT
    
    echo "✓ NAT configured ($WIFI_IFACE → $WAN_IFACE)"
fi

# Start services
echo ""
echo "Starting services..."

# Restart dnsmasq
systemctl restart dnsmasq
if systemctl is-active --quiet dnsmasq; then
    echo "✓ DHCP/DNS server started"
else
    echo "⚠️  DHCP/DNS may not have started - check: systemctl status dnsmasq"
fi

# Start hostapd
systemctl unmask hostapd 2>/dev/null
systemctl enable hostapd 2>/dev/null
systemctl restart hostapd

echo ""
echo "Waiting for hostapd to start..."
sleep 3

if systemctl is-active --quiet hostapd; then
    echo "✓ Wi-Fi Access Point started"
else
    echo "✗ Failed to start Access Point"
    echo "  Check logs: journalctl -xeu hostapd"
    exit 1
fi

# Display summary
echo ""
echo "========================================="
echo "✓ Wi-Fi Access Point is Running!"
echo "========================================="
echo ""
echo "Network Details:"
echo "  SSID: $ssid"
echo "  Password: ********"
echo "  Security: WPA2-PSK"
echo "  Channel: $channel"
echo "  Interface: $WIFI_IFACE"
echo "  Gateway: 192.168.10.1"
echo "  DHCP Range: 192.168.10.100 - 192.168.10.200"
if [ -n "$WAN_IFACE" ]; then
    echo "  Internet: $WAN_IFACE (NAT enabled)"
else
    echo "  Internet: Not configured"
fi
echo ""
echo "Commands:"
echo "  View logs:    journalctl -fu hostapd"
echo "  Stop AP:      systemctl stop hostapd"
echo "  Restart AP:   systemctl restart hostapd"
echo "  Status:       systemctl status hostapd"
echo ""
echo "Connect your devices to '$ssid' now!"
echo "========================================="
