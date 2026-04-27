# HaresNet

A Smart Linux-Based Wi-Fi Router for Secure Home and Small-Office Networks.

Built as a graduation project at Palestine Polytechnic University — 2026.

---

## Overview

HaresNet transforms a standard Linux computer into a fully manageable
Wi-Fi router with enterprise-grade features, using:

- **hostapd** — Wi-Fi Access Point (WPA2/WPA3)
- **dnsmasq** — DHCP/DNS services
- **nftables** — Firewall and traffic control
- **Flask** — REST API backend
- **React** — Guardian Angel web dashboard

---

## Features

- Real-time device discovery and monitoring
- Per-device internet blocking / unblocking
- Time-based access scheduling
- Service and URL blocking (firewall-enforced)
- Traffic monitoring with historical charts
- Daily/hourly traffic limits with alerts
- Two-factor authentication (2FA/OTP)
- Push notifications (NTFY, Email, Blynk)
- Parental control / child mode
- Internet speed test

---

## Project Structure

```
HaresNet/
├── haresnet-backend/
│   ├── app/
│   ├── scripts/
│   ├── Dockerfile
│   └── docker-compose.yml
└── guardian-angel/
    ├── src/
    └── public/
```

## Requirements

- Ubuntu 22.04
- Python 3.10+
- Node.js 18+
- Docker (optional)
- USB Wi-Fi adapter (AP mode support)

---

## Run with Docker

```bash
cd haresnet-backend
docker-compose up --build
```

## Run manually

```bash
# Backend
cd haresnet-backend
pip install -r requirements.txt
python run.py

# Frontend
cd guardian-angel
npm install
npm run dev
```

---

## Author

**Ismael Rjoub**

