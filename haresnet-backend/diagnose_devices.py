#!/usr/bin/env python3
"""
Diagnostic script to check device discovery status
Run this inside the Docker container or with proper permissions
"""
import sys
import os
sys.path.insert(0, '/app')

from app import create_app, db
from app.models import Device
from app.services.device_discovery import DeviceDiscovery
from datetime import datetime

app = create_app()

def diagnose():
    with app.app_context():
        discovery = DeviceDiscovery()
        
        print("=" * 80)
        print("DEVICE DISCOVERY DIAGNOSTIC")
        print("=" * 80)
        
        # Check WiFi interface
        print(f"\n[1] WiFi Interface: {discovery.wifi_interface}")
        print(f"    Exists: {os.path.exists(f'/sys/class/net/{discovery.wifi_interface}')}")
        
        # Check WiFi stations
        print(f"\n[2] WiFi Stations:")
        wifi_stations, wifi_success = discovery.discover_from_wifi_stations()
        print(f"    Success: {wifi_success}")
        print(f"    Count: {len(wifi_stations)}")
        for mac, inactive_ms in wifi_stations.items():
            print(f"    - {mac}: {inactive_ms}ms inactive")
        
        # Check ARP
        print(f"\n[3] ARP Devices:")
        arp_devices = discovery.discover_from_arp()
        print(f"    Count: {len(arp_devices)}")
        for dev in arp_devices:
            print(f"    - {dev['mac']}: {dev['ip']} on {dev.get('interface', 'N/A')}")
        
        # Check DHCP
        print(f"\n[4] DHCP Leases:")
        dhcp_devices = discovery.discover_from_dhcp_leases()
        print(f"    Count: {len(dhcp_devices)}")
        for dev in dhcp_devices:
            print(f"    - {dev['mac']}: {dev['ip']}")
        
        # Check database
        print(f"\n[5] Database Devices:")
        devices = Device.query.all()
        now = datetime.utcnow()
        print(f"    Count: {len(devices)}")
        for device in devices:
            if device.last_seen:
                diff = (now - device.last_seen).total_seconds()
                is_online = diff < 45
                in_wifi = device.mac in wifi_stations
                in_arp = any(d['mac'] == device.mac for d in arp_devices)
                
                print(f"    - {device.mac} ({device.hostname or device.ip or 'N/A'})")
                print(f"      Last seen: {diff:.1f}s ago")
                print(f"      Status: {'ONLINE' if is_online else 'OFFLINE'}")
                print(f"      In WiFi: {in_wifi}")
                print(f"      In ARP: {in_arp}")
        
        print("\n" + "=" * 80)

if __name__ == "__main__":
    diagnose()
