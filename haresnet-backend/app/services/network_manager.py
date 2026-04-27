
import os
import subprocess
import json
import time
from app import db
from app.models import SystemSettings

class NetworkManager:
    """Manages network configuration, scanning, and mode switching"""
    
    def __init__(self):
        self.wifi_interface = os.environ.get('LAN_INTERFACE', 'wlan0')
        self.script_path = '/app/scripts/switch_mode.sh'
        
    def get_available_networks(self):
        """Scan for available Wi-Fi networks"""
        networks = []
        try:
            # Check if hostapd is running
            hostapd_running = subprocess.run(['pgrep', 'hostapd'], capture_output=True).returncode == 0
            
            if hostapd_running:
                print("Stopping hostapd to scan...")
                subprocess.run(['pkill', 'hostapd'], check=False)
                time.sleep(1) # Give it a moment to release the interface

                # Bring interface down/up to reset state
                subprocess.run(['ip', 'link', 'set', self.wifi_interface, 'down'], check=False)
                subprocess.run(['ip', 'link', 'set', self.wifi_interface, 'up'], check=False)
                time.sleep(1)

            # Perform Scan
            cmd = ['iw', 'dev', self.wifi_interface, 'scan']
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            # Restart hostapd if it was running
            if hostapd_running:
                print("Restarting hostapd...")
                subprocess.run(['hostapd', '-B', '/etc/hostapd/hostapd.conf'], check=False)
            
            if result.returncode != 0:
                print(f"Scan failed: {result.stderr}")
                return []
                
            # Parse iw scan output (improved parsing)
            current_net = {}
            for line in result.stdout.split('\n'):
                line = line.strip()
                if line.startswith('BSS '):
                    if current_net and 'ssid' in current_net:
                        networks.append(current_net)
                    current_net = {'bssid': line.split('(')[0].split()[1]}
                elif line.startswith('SSID:'):
                    current_net['ssid'] = line.split(':', 1)[1].strip()
                elif line.startswith('signal:'):
                    # Extract signal strength in dBm (e.g., "signal: -45.00 dBm" -> "-45")
                    signal_str = line.split(':')[1].strip().split()[0]
                    try:
                        current_net['signal'] = int(float(signal_str))
                        current_net['signal_dbm'] = f"{signal_str} dBm"
                    except:
                        current_net['signal'] = -100
                        current_net['signal_dbm'] = "Unknown"
                elif 'WPA:' in line:
                    current_net['security'] = 'WPA'
                elif 'RSN:' in line or 'WPA2' in line:
                    current_net['security'] = 'WPA2'
                elif 'SAE' in line or 'WPA3' in line:
                    current_net['security'] = 'WPA3'
            
            if current_net and 'ssid' in current_net:
                networks.append(current_net)
                
            # Dedup by SSID, keeping strongest signal
            deduped = {}
            for net in networks:
                ssid = net.get('ssid')
                if not ssid:
                    continue
                    
                # Default signal if not set
                if 'signal' not in net:
                    net['signal'] = -100
                    
                # If we already have this SSID, check if new one is better
                if ssid in deduped:
                    if net.get('signal', -100) > deduped[ssid].get('signal', -100):
                        deduped[ssid] = net
                else:
                    deduped[ssid] = net
            
            # Sort by signal strength (strongest first)
            sorted_networks = sorted(deduped.values(), key=lambda x: x.get('signal', -100), reverse=True)
            
            return sorted_networks
            
        except Exception as e:
            print(f"Error scanning networks: {e}")
            return []

    def get_current_config(self):
        """Get current network configuration from DB"""
        mode = SystemSettings.query.filter_by(key='network_mode').first()
        ssid = SystemSettings.query.filter_by(key='upstream_ssid').first()
        
        config = {
            'mode': mode.value if mode else 'router',
            'upstream_ssid': ssid.value if ssid else None
        }
        
        # Add repeater configuration if in repeater mode
        if config['mode'] == 'repeater':
            repeater_ssid = SystemSettings.query.filter_by(key='repeater_ssid').first()
            repeater_security = SystemSettings.query.filter_by(key='repeater_security_mode').first()
            repeater_channel = SystemSettings.query.filter_by(key='repeater_channel').first()
            repeater_hidden = SystemSettings.query.filter_by(key='repeater_hidden').first()
            
            config.update({
                'repeater_ssid': repeater_ssid.value if repeater_ssid else None,
                'repeater_security_mode': repeater_security.value if repeater_security else 'WPA2',
                'repeater_channel': int(repeater_channel.value) if repeater_channel else 6,
                'repeater_hidden': repeater_hidden.value == 'true' if repeater_hidden else False
            })
        
        return config

    def set_mode(self, mode, upstream_ssid=None, upstream_password=None, repeater_config=None):
        """Configure network mode (router/repeater)"""
        
        # 1. Update Settings in DB
        self._update_setting('network_mode', mode)
        if upstream_ssid:
            self._update_setting('upstream_ssid', upstream_ssid)
        if upstream_password:
            self._update_setting('upstream_password', upstream_password)
        
        # Store repeater WiFi configuration
        if mode == 'repeater' and repeater_config:
            if repeater_config.get('ssid'):
                self._update_setting('repeater_ssid', repeater_config['ssid'])
            if repeater_config.get('password'):
                self._update_setting('repeater_password', repeater_config['password'])
            self._update_setting('repeater_security_mode', repeater_config.get('security_mode', 'WPA2'))
            self._update_setting('repeater_channel', str(repeater_config.get('channel', 6)))
            self._update_setting('repeater_hidden', 'true' if repeater_config.get('hidden', False) else 'false')
            
        # 2. Trigger shell script to apply changes
        # We run this async or detach because it might kill the network interface we are using!
        # But if it's localhost (docker), it might be fine.
        
        try:
            # Make sure script exists
            if not os.path.exists(self.script_path):
                print(f"Error: Script {self.script_path} not found")
                return False, "Configuration script missing"

            cmd = [self.script_path, mode]
            if mode == 'repeater':
                if not upstream_ssid or not upstream_password:
                    return False, "SSID and Password required for Repeater mode"
                
                # Pass upstream credentials
                cmd.extend([upstream_ssid, upstream_password])
                
                # Pass repeater WiFi configuration
                if repeater_config:
                    repeater_ssid = repeater_config.get('ssid', 'HaresNet-Extended')
                    repeater_password = repeater_config.get('password', 'haresnet2024')
                    repeater_security = repeater_config.get('security_mode', 'WPA2')
                    repeater_channel = str(repeater_config.get('channel', 6))
                    repeater_hidden = '1' if repeater_config.get('hidden', False) else '0'
                    
                    cmd.extend([repeater_ssid, repeater_password, repeater_security, repeater_channel, repeater_hidden])
            
            # Use subprocess to run the script
            # Note: This might disrupt connectivity if the user is connected via Wi-Fi!
            subprocess.Popen(cmd)
            
            return True, "Mode configuration started. Network will restart."
            
        except Exception as e:
            return False, str(e)

    def _update_setting(self, key, value):
        setting = SystemSettings.query.filter_by(key=key).first()
        if not setting:
            setting = SystemSettings(key=key, value=value)
            db.session.add(setting)
        else:
            setting.value = value
        db.session.commit()
