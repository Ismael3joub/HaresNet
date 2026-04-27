# HaresNet Backend

A Flask-based backend API for the HaresNet Wi-Fi router platform. This backend manages Wi-Fi access points, device tracking, firewall rules, and scheduling using Docker.

## Features

- **Authentication**: JWT-based user authentication
- **Device Management**: Track and manage connected devices via DHCP/ARP
- **Wi-Fi Configuration**: Configure SSID, password, and security (WPA2/WPA3)
- **Firewall**: nftables-based firewall with NAT and per-device blocking
- **Scheduling**: Time-based access control for devices
- **System Monitoring**: CPU, memory, network statistics

## Prerequisites

- Docker and Docker Compose
- USB Wi-Fi adapter with AP mode support
- Ethernet connection for WAN

## Quick Start

1. **Configure Environment Variables**

   Edit `docker-compose.yml` and set:
   - `WAN_INTERFACE`: Your Ethernet interface (e.g., `eth0`)
   - `LAN_INTERFACE`: Your Wi-Fi interface (e.g., `wlan0`)
   - `SECRET_KEY` and `JWT_SECRET_KEY`: Generate secure random strings

2. **Build and Run**

   ```bash
   docker-compose up -d
   ```

3. **Access the API**

   The API will be available at `http://localhost:5000/api`

   Default credentials:
   - Username: `admin`
   - Password: `haresnet2024`

## API Endpoints

### Authentication
- `POST /api/auth/login` - Login
- `POST /api/auth/logout` - Logout
- `GET /api/auth/status` - Check auth status
- `POST /api/auth/change-password` - Change password

### Devices
- `GET /api/devices` - List all devices
- `GET /api/devices/:id` - Get device details
- `PUT /api/devices/:id` - Update device
- `POST /api/devices/:id/block` - Block device
- `POST /api/devices/:id/unblock` - Unblock device
- `DELETE /api/devices/:id` - Forget device

### Wi-Fi
- `GET /api/wifi/config` - Get Wi-Fi config
- `PUT /api/wifi/config` - Update Wi-Fi config
- `POST /api/wifi/restart` - Restart access point
- `GET /api/wifi/status` - Get AP status

### Firewall
- `GET /api/firewall/rules` - List firewall rules
- `GET /api/firewall/status` - Get firewall status
- `POST /api/firewall/apply` - Apply rules

### Schedules
- `GET /api/schedules` - List schedules
- `POST /api/schedules` - Create schedule
- `PUT /api/schedules/:id` - Update schedule
- `DELETE /api/schedules/:id` - Delete schedule
- `POST /api/schedules/:id/toggle` - Enable/disable schedule

### System
- `GET /api/system/status` - System status
- `GET /api/system/interfaces` - Network interfaces
- `GET /api/system/network-stats` - Network statistics

## Architecture

```
├── app/
│   ├── api/              # API endpoints
│   ├── models.py         # Database models
│   ├── services/         # Business logic
│   │   ├── device_discovery.py
│   │   ├── hostapd_manager.py
│   │   ├── nftables_manager.py
│   │   ├── dnsmasq_manager.py
│   │   └── scheduler.py
│   └── utils/
├── config.py             # Configuration
├── run.py                # Application entry point
├── Dockerfile
└── docker-compose.yml
```

## Development

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run locally (requires root for network operations):
   ```bash
   sudo python3 run.py
   ```

## Security Notes

- Change default credentials immediately
- Use strong, unique passwords
- Keep the container updated
- Monitor logs for suspicious activity

## License

This project is part of the HaresNet platform.
