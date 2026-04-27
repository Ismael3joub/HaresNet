#!/usr/bin/env python3
"""
Reset WiFi configuration to safe router-only defaults
Run this inside the container to clear any problematic settings
"""

import sys
import os

# Add current directory to path
sys.path.append(os.getcwd())

from app import create_app, db
from app.models import WiFiConfig, SystemSettings

def reset_wifi_config():
    """Reset WiFi configuration to router-only defaults"""
    app = create_app()
    
    with app.app_context():
        print("=" * 50)
        print("Resetting WiFi Configuration to Router Defaults")
        print("=" * 50)
        
        # 1. Clear all repeater-related settings
        print("\n1. Removing repeater settings...")
        repeater_keys = [
            'repeater_ssid',
            'repeater_password',
            'repeater_security_mode',
            'repeater_channel',
            'repeater_hidden',
            'upstream_ssid',
            'upstream_password'
        ]
        
        for key in repeater_keys:
            setting = SystemSettings.query.filter_by(key=key).first()
            if setting:
                db.session.delete(setting)
                print(f"   - Removed: {key}")
        
        # 2. Reset WiFiConfig to safe defaults
        print("\n2. Resetting WiFiConfig...")
        config = WiFiConfig.query.first()
        
        if config:
            # Update existing config
            config.ssid = 'HaresNet'
            config.password = 'haresnet2024'
            config.security_mode = 'WPA2'
            config.band = '2.4GHz'  # Force 2.4GHz
            config.channel = 6
            config.hidden = False
            print("   - Updated existing WiFiConfig")
        else:
            # Create new config
            config = WiFiConfig(
                ssid='HaresNet',
                password='haresnet2024',
                security_mode='WPA2',
                band='2.4GHz',
                channel=6,
                hidden=False
            )
            db.session.add(config)
            print("   - Created new WiFiConfig")
        
        # 3. Commit all changes
        db.session.commit()
        
        print("\n" + "=" * 50)
        print("✓ WiFi Configuration Reset Complete")
        print("=" * 50)
        print("\nCurrent Router WiFi Settings:")
        print(f"  SSID: {config.ssid}")
        print(f"  Password: {config.password}")
        print(f"  Security: {config.security_mode}")
        print(f"  Band: {config.band}")
        print(f"  Channel: {config.channel}")
        print(f"  Hidden: {config.hidden}")
        print("\nRestart the container for changes to take effect.")

if __name__ == "__main__":
    reset_wifi_config()
