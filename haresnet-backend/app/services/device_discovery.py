import os
import re
from datetime import datetime, timedelta
from app import db
from app.models import Device
from flask import current_app
import subprocess
import shutil

class DeviceDiscovery:
    """Discovers and tracks connected devices"""
    
    def __init__(self):
        self.leases_file = '/var/lib/misc/dnsmasq.leases'
        self.arp_file = '/proc/net/arp'
        self.oui_db = self._load_oui_database()
        self.wifi_interface = os.environ.get('LAN_INTERFACE', 'wlan0')
    
    def _load_oui_database(self):
        """Load MAC vendor OUI database (simplified)"""
        # In a real implementation, this would load from a proper OUI database
        # For now, return a simple mapping
        return {
            '00:0C:29': 'VMware',
            '00:50:56': 'VMware',
            '08:00:27': 'VirtualBox',
            'B8:27:EB': 'Raspberry Pi Foundation',
            'DC:A6:32': 'Raspberry Pi Foundation',
            'E4:5F:01': 'Raspberry Pi Foundation',
        }
    
    def _get_vendor_from_mac(self, mac):
        """Get vendor name from MAC address OUI"""
        if not mac:
            return None
        
        # Extract OUI (first 3 octets)
        oui = ':'.join(mac.upper().split(':')[:3])
        return self.oui_db.get(oui, 'Unknown')
    
    def discover_from_dhcp_leases(self):
        """Discover devices from dnsmasq DHCP leases"""
        devices = []
        
        if not os.path.exists(self.leases_file):
            return devices
        
        try:
            with open(self.leases_file, 'r') as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) >= 4:
                        # Format: timestamp MAC IP hostname [client-id]
                        timestamp = parts[0]
                        mac = parts[1]
                        ip = parts[2]
                        hostname = parts[3] if parts[3] != '*' else None
                        
                        devices.append({
                            'mac': mac,
                            'ip': ip,
                            'hostname': hostname,
                            'vendor': self._get_vendor_from_mac(mac)
                        })
        except Exception as e:
            print(f"Error reading DHCP leases: {str(e)}")
        
        return devices
    
    def discover_from_arp(self):
        """Discover devices from ARP table"""
        devices = []
        
        if not os.path.exists(self.arp_file):
            return devices
        
        try:
            with open(self.arp_file, 'r') as f:
                lines = f.readlines()[1:]  # Skip header
                
                for line in lines:
                    parts = line.strip().split()
                    if len(parts) >= 6:
                        ip = parts[0]
                        mac = parts[3]
                        interface = parts[5]
                        
                        # Filter out non-LAN devices (e.g. Docker bridges, WAN)
                        if interface != self.wifi_interface:
                            continue
                        
                        # Skip incomplete entries
                        if mac == '00:00:00:00:00:00' or mac == '<incomplete>':
                            continue
                        
                        devices.append({
                            'mac': mac,
                            'ip': ip,
                            'hostname': None,
                            'interface': interface,
                            'vendor': self._get_vendor_from_mac(mac)
                        })
        except Exception as e:
            print(f"Error reading ARP table: {str(e)}")
        
        return devices

    def discover_from_wifi_stations(self):
        """Discover devices currently connected to Wi-Fi AP"""
        # Map of MAC -> Inactive time (ms)
        connected_stations = {}
        success = False
        
        # Check if interface exists
        if not os.path.exists(f"/sys/class/net/{self.wifi_interface}"):
            return connected_stations, False
            
        try:
            # Use iw to dump connected stations
            cmd = ['iw', 'dev', self.wifi_interface, 'station', 'dump']
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                success = True
                current_mac = None
                
                # Parse output
                for line in result.stdout.split('\n'):
                    line = line.strip()
                    if line.startswith('Station'):
                        parts = line.split()
                        if len(parts) >= 2:
                            current_mac = parts[1]
                            connected_stations[current_mac] = 0 # Default if parse fails
                    elif line.startswith('inactive time:') and current_mac:
                        # Format: inactive time:	304 ms
                        try:
                            time_str = line.split(':')[1].strip().split()[0]
                            connected_stations[current_mac] = int(time_str)
                        except (IndexError, ValueError):
                            pass
        except Exception as e:
            print(f"Error discovering connected stations: {str(e)}")
            
        return connected_stations, success
    
    def update_device_database(self):
        """Update device database with discovered devices"""
        # Combine devices from all sources
        dhcp_devices = self.discover_from_dhcp_leases()
        arp_devices = self.discover_from_arp()
        wifi_stations, wifi_success = self.discover_from_wifi_stations()
        
        # Create a map by MAC address
        device_map = {}
        
        # Helper to track active interfaces per MAC
        mac_interfaces = {}

        for device in arp_devices:
            mac_interfaces[device['mac']] = device.get('interface')
        
        # ... (rest of function logic needs update)

        for device in dhcp_devices + arp_devices:
             # ... (merging logic)
             pass 

        # I need to be careful with replace_file_content not to break the file structure.
        # I will replace the start of `update_device_database` to unpack the tuple.


        for device in dhcp_devices + arp_devices:
            mac = device['mac']
            if mac in device_map:
                # Merge information (DHCP info is preferred for hostname)
                if device.get('hostname'):
                    device_map[mac]['hostname'] = device['hostname']
                if device.get('ip'):
                    device_map[mac]['ip'] = device['ip']
            else:
                device_map[mac] = device
        
        # Update database
        now = datetime.utcnow()
        
        for mac, info in device_map.items():
            device = Device.query.filter_by(mac=mac).first()
            
            if device:
                # Update existing device info (IP, Hostname)
                # But DO NOT update last_seen yet
                device.ip = info.get('ip')
                device.hostname = info.get('hostname')
                device.vendor = info.get('vendor')
                # device.last_seen = now  <-- REMOVED: Caused false positives via DHCP
            else:
                # Create new device
                device = Device(
                    mac=mac,
                    ip=info.get('ip'),
                    hostname=info.get('hostname'),
                    vendor=info.get('vendor'),
                    first_seen=now,
                    last_seen=now # Initial last_seen is fine
                )
                db.session.add(device)
                db.session.flush() # Get device ID
                
                # Notify NTFY of new device
                try:
                    from app.services.ntfy_service import NtfyService
                    ntfy = NtfyService()
                    ntfy.notify_new_device(device)
                except Exception as ntfy_err:
                    print(f"NTFY notification error: {str(ntfy_err)}")
            
            # Smart Last Seen Update Logic
            # Smart Last Seen Update Logic
            # Update last_seen if device appears in any discovery source (wifi, arp, dhcp)
            should_update_seen = False

            # Case 1: Device is in WiFi station list (Active WiFi connection)
            if mac in wifi_stations:
                inactive_ms = wifi_stations[mac]
                # If station reports recent activity (< 30s), consider it online
                if inactive_ms < 30000:
                    should_update_seen = True
            
            # Case 2: Device is in ARP table
            elif mac in mac_interfaces:
                device_iface = mac_interfaces.get(mac)
                
                # Check if this MAC belongs to the WiFi interface
                is_wifi_device = (device_iface == self.wifi_interface)
                
                if is_wifi_device:
                    # If it's a WiFi device, we ONLY trust ARP if looking up stations failed.
                    # If looking up stations SUCCEEDED (wifi_success=True) and it's NOT in the list,
                    # then the device is Disconnected (stale ARP).
                    if not wifi_success:
                        # Fallback: We can't query stations, so we have to trust ARP (imperfect)
                        should_update_seen = True
                    else:
                        # We successfully queried stations and it wasn't there -> OFF.
                        should_update_seen = False
                else:
                    # Wired device (not on wifi interface) -> Trust ARP
                    should_update_seen = True

            if should_update_seen:
                device.last_seen = now
                # Ensure accounting rule exists for active devices
                if device.ip:
                    from app.services.nftables_manager import NftablesManager
                    nft_mgr = NftablesManager()
                    try:
                        nft_mgr.add_accounting_rule(device.ip)
                    except Exception:
                        pass
            # else: 
            #    We do NOT touch last_seen. Logic in models.py (diff < 45s) will handle "offline" status.
        
        try:
            db.session.commit()
            
            # Emit update event via Socket.IO
            from app import socketio
            socketio.emit('device_update', {'timestamp': now.isoformat()})
            
            return True
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating device database: {str(e)}")
            return False
        finally:
            db.session.remove()
