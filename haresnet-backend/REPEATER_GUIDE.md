# Unified Repeater Configuration - Quick Reference

## API Quick Reference

### Network Scanning
```bash
GET /api/network/scan
```
Returns available WiFi networks sorted by signal strength.

### Switch to Repeater Mode
```bash
POST /api/network/mode
Content-Type: application/json

{
  "mode": "repeater",
  "upstream_ssid": "NetworkToExtend",
  "upstream_password": "password123",
  "repeater_ssid": "MyExtendedNetwork",
  "repeater_password": "extendedpass456",
  "repeater_security_mode": "WPA2",
  "repeater_channel": 6,
  "repeater_hidden": false
}
```

### Switch to Router Mode
```bash
POST /api/network/mode
Content-Type: application/json

{
  "mode": "router"
}
```

### Get WiFi Config (Mode-Aware)
```bash
GET /api/wifi/config?mode=repeater
GET /api/wifi/config?mode=router
```

### Update WiFi Config (Mode-Aware)
```bash
PUT /api/wifi/config
Content-Type: application/json

{
  "mode": "repeater",
  "ssid": "NewSSID",
  "password": "newpassword",
  "security_mode": "WPA2/WPA3",
  "channel": 11,
  "hidden": false
}
```

## Configuration Parameters

| Parameter | Values | Description |
|-----------|--------|-------------|
| `mode` | `router`, `repeater` | Operating mode |
| `upstream_ssid` | String (1-32 chars) | Network to connect to (repeater only) |
| `upstream_password` | String (8-63 chars) | Upstream network password |
| `repeater_ssid` | String (1-32 chars) | SSID to broadcast (repeater only) |
| `repeater_password` | String (8-63 chars) | Password for extended network |
| `repeater_security_mode` | `WPA2`, `WPA3`, `WPA2/WPA3` | Security mode |
| `repeater_channel` | 1-13 | WiFi channel |
| `repeater_hidden` | `true`, `false` | Hide SSID broadcast |

## How It Works

### Router Mode
- Device creates its own WiFi network
- Uses `wlan0` interface as access point
- Network: `192.168.10.0/24`
- NAT to WAN interface

### Repeater Mode
- `wlan0` connects to upstream WiFi as client
- `uap0` virtual interface broadcasts extended network
- Network: `192.168.20.0/24`
- NAT from `uap0` to `wlan0`
- **Custom SSID** different from upstream

## Files Modified

| File | Changes |
|------|---------|
| `app/api/network.py` | Enhanced mode endpoint with repeater config |
| `app/api/wifi.py` | Added mode-aware WiFi config endpoints |
| `app/services/network_manager.py` | Added repeater config handling & improved scanning |
| `app/services/hostapd_manager.py` | Added repeater config generation method |
| `scripts/switch_mode.sh` | Enhanced to configure repeater with all settings |

## Database Settings

Configuration stored in `SystemSettings` table:
- `network_mode`
- `upstream_ssid`, `upstream_password`
- `repeater_ssid`, `repeater_password`
- `repeater_security_mode`, `repeater_channel`, `repeater_hidden`

## Key Features

✅ Scan and select upstream networks  
✅ Custom repeater SSID (different from upstream)  
✅ Full WiFi configuration control in both modes  
✅ All security modes supported (WPA2, WPA3, mixed)  
✅ Channel selection and hidden SSID support  
✅ Configuration persistence across restarts  
✅ Signal strength sorted network list  

## Example: Complete Setup Flow

```bash
# 1. Scan for networks
curl GET /api/network/scan

# 2. Configure repeater with custom settings
curl POST /api/network/mode \
  -d '{
    "mode": "repeater",
    "upstream_ssid": "CoffeeShop",
    "upstream_password": "coffeepass",
    "repeater_ssid": "MyCoffeeExtended",
    "repeater_password": "mysecurepass",
    "repeater_security_mode": "WPA2",
    "repeater_channel": 11
  }'

# 3. Verify configuration
curl GET /api/network/config

# 4. Later, switch back to router
curl POST /api/network/mode -d '{"mode": "router"}'
```
