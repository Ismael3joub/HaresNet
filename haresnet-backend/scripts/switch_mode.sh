#!/bin/bash
# switch_mode.sh
# Usage: ./switch_mode.sh [router|repeater] [upstream_ssid] [upstream_password] [repeater_ssid] [repeater_password] [security_mode] [channel] [hidden]

MODE=$1
UPSTREAM_SSID=$2
UPSTREAM_PASSWORD=$3
REPEATER_SSID=$4
REPEATER_PASSWORD=$5
REPEATER_SECURITY=$6
REPEATER_CHANNEL=$7
REPEATER_HIDDEN=$8

LOGfile="/var/log/network_mode.log"
exec >> $LOGfile 2>&1

echo "--- Switching to $MODE mode ($(date)) ---"

# Load current interface
WIFI_IFACE=${LAN_INTERFACE:-wlan0}

kill_services() {
    echo "Stopping services..."
    pkill -9 hostapd 2>/dev/null || true
    pkill -9 wpa_supplicant 2>/dev/null || true
    pkill -9 dnsmasq 2>/dev/null || true
    
    # Clean up virtual interface if it exists
    if ip link show uap0 >/dev/null 2>&1; then
        echo "Removing existing uap0 interface..."
        ip link set uap0 down 2>/dev/null || true
        iw dev uap0 del 2>/dev/null || true
    fi
    
    # Flush firewall rules
    nft flush ruleset 2>/dev/null || true
    
    sleep 2
}

setup_router_mode() {
    echo "Configuring Router Mode..."
    # Simply ensure hostapd is running on main interface
    # (Assuming entrypoint logic or standard config)
    
    # 1. Kill wpa_supplicant (client mode)
    pkill wpa_supplicant
    
    # 2. Reset Interface
    ip link set $WIFI_IFACE down
    iw dev uap0 del 2>/dev/null  # Remove virtual interface if exists
    ip addr flush dev $WIFI_IFACE
    ip link set $WIFI_IFACE up
    
    # 3. Configure IP
    ip addr add 192.168.10.1/24 dev $WIFI_IFACE
    
    # 4. Start hostapd
    hostapd -B /etc/hostapd/hostapd.conf
    
    # 5. Start dnsmasq
    echo "Configuring dnsmasq..."
    if [ ! -f /etc/dnsmasq.conf ]; then
        echo "Creating default /etc/dnsmasq.conf..."
        cat > /etc/dnsmasq.conf <<EOF
interface=$WIFI_IFACE
no-dhcp-interface=eth0
dhcp-range=192.168.10.100,192.168.10.200,12h
dhcp-option=3,192.168.10.1
dhcp-option=6,192.168.10.1
domain=haresnet.local
no-resolv
server=8.8.8.8
server=8.8.4.4
EOF
    fi

    dnsmasq --conf-file=/etc/dnsmasq.conf
    
    # 6. NFTables (NAT from WIFI to ETH0 usually)
    # We assume standard NAT setup script or existing saved rules
    # For now, re-run basic NAT setup for WAN=eth0
    WAN_IFACE=$(ip route show default | awk '/default/ {print $5}')
    if [ -z "$WAN_IFACE" ]; then WAN_IFACE="enp3s0"; fi # Fallback
    
    nft add table inet haresnet
    nft add chain inet haresnet postrouting { type nat hook postrouting priority 100\; }
    nft add rule inet haresnet postrouting oifname "$WAN_IFACE" masquerade
    
    echo "Router Mode Configured"
}

setup_repeater_mode() {
    echo "Configuring Repeater Mode..."
    
    # Set defaults if parameters not provided
    REPEATER_SSID=${REPEATER_SSID:-"HaresNet-Extended"}
    REPEATER_PASSWORD=${REPEATER_PASSWORD:-"haresnet2024"}
    REPEATER_SECURITY=${REPEATER_SECURITY:-"WPA2"}
    REPEATER_CHANNEL=${REPEATER_CHANNEL:-6}
    REPEATER_HIDDEN=${REPEATER_HIDDEN:-0}
    
    # 1. Create wpa_supplicant config for upstream connection
    cat > /etc/wpa_supplicant/wpa_supplicant.conf <<EOF
ctrl_interface=/var/run/wpa_supplicant
update_config=1
country=US

network={
    ssid="$UPSTREAM_SSID"
    psk="$UPSTREAM_PASSWORD"
}
EOF

    # 2. Create Virtual Interface for AP (uap0) because wlan0 will be client
    # Note: This depends on driver support (iw list | grep "valid interface combinations")
    echo "Creating virtual AP interface uap0..."
    iw dev $WIFI_IFACE interface add uap0 type __ap
    
    # 3. Connect wlan0 to upstream
    echo "Starting wpa_supplicant on $WIFI_IFACE..."
    wpa_supplicant -B -i $WIFI_IFACE -c /etc/wpa_supplicant/wpa_supplicant.conf
    
    # Get IP for wlan0 via DHCP
    echo "Getting IP for $WIFI_IFACE..."
    dhclient $WIFI_IFACE
    
    # 4. Configure AP on uap0
    echo "Configuring AP on uap0..."
    ip link set uap0 up
    ip addr add 192.168.20.1/24 dev uap0  # DIFFERENT SUBNET than standard 192.168.10.1
    
    # 5. Generate hostapd config for repeater with custom settings
    echo "Generating repeater hostapd configuration..."
    
    # Determine security settings based on mode
    if [ "$REPEATER_SECURITY" = "WPA3" ]; then
        WPA_VALUE=2
        WPA_KEY_MGMT="SAE"
        RSN_PAIRWISE="CCMP"
        IEEE80211W=2
    elif [ "$REPEATER_SECURITY" = "WPA2/WPA3" ]; then
        WPA_VALUE=2
        WPA_KEY_MGMT="WPA-PSK SAE"
        RSN_PAIRWISE="CCMP"
        IEEE80211W=1
    else
        # WPA2 (default)
        WPA_VALUE=2
        WPA_KEY_MGMT="WPA-PSK"
        RSN_PAIRWISE="CCMP"
        IEEE80211W=0
    fi
    
    cat > /etc/hostapd/hostapd_repeater.conf <<EOF
interface=uap0
driver=nl80211
ssid=$REPEATER_SSID
hw_mode=g
channel=$REPEATER_CHANNEL
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=$REPEATER_HIDDEN

# Security settings
wpa=$WPA_VALUE
wpa_key_mgmt=$WPA_KEY_MGMT
wpa_passphrase=$REPEATER_PASSWORD
rsn_pairwise=$RSN_PAIRWISE

# IEEE 802.11w Management Frame Protection
ieee80211w=$IEEE80211W

# Additional settings
wmm_enabled=1
EOF

    echo "Starting hostapd on uap0..."
    hostapd -B /etc/hostapd/hostapd_repeater.conf
    
    # 6. Dnsmasq for uap0
    echo "Configuring dnsmasq for uap0..."
    cat > /etc/dnsmasq_repeater.conf <<EOF
interface=uap0
bind-interfaces
dhcp-range=192.168.20.100,192.168.20.200,12h
dhcp-option=3,192.168.20.1
dhcp-option=6,192.168.20.1
server=8.8.8.8
log-facility=/var/log/dnsmasq_repeater.log
EOF
    
    dnsmasq --conf-file=/etc/dnsmasq_repeater.conf
    
    # 7. NAT: uap0 -> wlan0
    echo "Configuring NAT: uap0 -> $WIFI_IFACE"
    nft add table inet haresnet
    nft add chain inet haresnet postrouting { type nat hook postrouting priority 100\; }
    nft add rule inet haresnet postrouting oifname "$WIFI_IFACE" masquerade
    
    echo "Repeater Mode Configured"
    echo "  Upstream Network: $UPSTREAM_SSID"
    echo "  Repeater SSID: $REPEATER_SSID"
    echo "  Security: $REPEATER_SECURITY"
    echo "  Channel: $REPEATER_CHANNEL"
    echo "  Hidden: $REPEATER_HIDDEN"
}

kill_services

if [ "$MODE" = "repeater" ]; then
    setup_repeater_mode
else
    setup_router_mode
fi
