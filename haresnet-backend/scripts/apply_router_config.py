
import sys
import os
import time

# Add current directory to path
sys.path.append(os.getcwd())

from app import create_app, db
from app.models import RouterConfig, WiFiConfig, SystemSettings
from app.services.network_interface_manager import NetworkInterfaceManager
from app.services.hostapd_manager import HostapdManager
from app.services.dnsmasq_manager import DnsmasqManager

def apply_config():
    """Apply all router configurations from database"""
    app = create_app()
    
    with app.app_context():
        print("Applying Router Configuration...")
        
        # 1. Apply Network Interface Settings (WAN/LAN)
        net_manager = NetworkInterfaceManager()
        
        config = RouterConfig.query.first()
        if not config:
            print("No RouterConfig found, using defaults")
            # Create default if missing
            config = RouterConfig()
            db.session.add(config)
            db.session.commit()
            
        print(f"Configuring WAN (Mode: {config.wan_mode})...")
        success, msg = net_manager.apply_wan_config(config)
        print(f"WAN: {msg}")
        if not success:
            print("WARNING: Failed to configure WAN")

        print(f"Configuring LAN (IP: {config.lan_ip})...")
        success, msg = net_manager.apply_lan_config(config)
        print(f"LAN: {msg}")
        if not success:
            print("WARNING: Failed to configure LAN")
            
        # 2. Generate and Apply DHCP/DNS Settings
        print("Configuring DHCP/DNS...")
        dnsmasq = DnsmasqManager()
        try:
            dnsmasq.generate_config()
            # We don't restart here, entrypoint will start it
            print("DNSmasq configuration generated")
        except Exception as e:
            print(f"Error generating DNSmasq config: {e}")

        # 3. Generate Wi-Fi Configuration
        print("Configuring Wi-Fi...")
        wifi_config = WiFiConfig.query.first()
        if not wifi_config:
            wifi_config = WiFiConfig(ssid='HaresNet', password='haresnet2024', band='2.4GHz')
            db.session.add(wifi_config)
            db.session.commit()
        else:
            # Force 2.4GHz for stability (router-only mode)
            if not wifi_config.band or wifi_config.band == '5GHz':
                wifi_config.band = '2.4GHz'
                db.session.commit()
                print("   - Enforced 2.4GHz band for stability")
            
        hostapd = HostapdManager()
        try:
            hostapd.generate_config(wifi_config)
            print("Hostapd configuration generated")
        except Exception as e:
            print(f"Error generating Hostapd config: {e}")
            
        print("Configuration application complete.")

if __name__ == "__main__":
    # Wait for DB to be ready (optional, or rely on entrypoint)
    apply_config()
