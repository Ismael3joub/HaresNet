import os
import subprocess
from flask import current_app

class HostapdManager:
    """Manages hostapd configuration and service"""
    
    def __init__(self):
        self.config_path = '/etc/hostapd/hostapd.conf'
        self.deny_path = '/etc/hostapd/hostapd.deny'
    
    def generate_config(self, wifi_config):
        """Generate hostapd configuration file"""
        from flask import current_app
        
        interface = current_app.config.get('LAN_INTERFACE', 'wlan0')
        
        # Map security mode to hostapd settings
        # Determine hardware mode based on band
        if hasattr(wifi_config, 'band') and wifi_config.band == '5GHz':
            hw_mode = 'a'
        else:
            hw_mode = 'g'
            
        # Handle auto channel
        channel = wifi_config.channel
        if channel == 0:  # 0 means auto in our logic
            channel = '0\nacs_num_scans=3'

        config_content = f"""# HaresNet hostapd configuration
interface={interface}
driver=nl80211
ssid={wifi_config.ssid}
hw_mode={hw_mode}
channel={channel}
ieee80211n=1
ieee80211ac=1
wmm_enabled=1
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid={'1' if wifi_config.hidden else '0'}
country_code=US
ieee80211d=1
deny_mac_file={self.deny_path}
ctrl_interface=/var/run/hostapd
ctrl_interface_group=0
"""

        # Append security settings
        if wifi_config.security_mode == 'WPA3':
            config_content += f"""wpa=2
wpa_passphrase={wifi_config.password}
wpa_key_mgmt=SAE
rsn_pairwise=CCMP
ieee80211w=2
"""
        elif wifi_config.security_mode == 'WPA2/WPA3':
            config_content += f"""wpa=2
wpa_passphrase={wifi_config.password}
wpa_key_mgmt=WPA-PSK SAE
rsn_pairwise=CCMP
ieee80211w=1
"""
        elif wifi_config.security_mode == 'WEP':
             # WEP is deprecated and insecure, but requested.
             # Hostapd WEP config is different.
             config_content += f"""wep_default_key=0
wep_key0={wifi_config.password}
auth_algs=2
"""
        elif wifi_config.security_mode == 'OPEN':
            # Open network (no WPA)
            pass
        else:  # Default to WPA2
            config_content += f"""wpa=2
wpa_passphrase={wifi_config.password}
wpa_key_mgmt=WPA-PSK
rsn_pairwise=CCMP
"""
        
        try:
            with open(self.config_path, 'w') as f:
                f.write(config_content)
                
            # Create empty deny file if not exists
            if not os.path.exists(self.deny_path):
                with open(self.deny_path, 'w') as f:
                    f.write("")
                    
            return True
        except Exception as e:
            raise Exception(f"Failed to write hostapd config: {str(e)}")
    
    def generate_repeater_config(self, ssid, password, security_mode='WPA2', channel=6, hidden=False):
        """Generate hostapd configuration for repeater mode (uap0 interface)"""
        interface = 'uap0'
        config_path = '/etc/hostapd/hostapd_repeater.conf'
        
        # Map security mode to hostapd settings
        if security_mode == 'WPA3':
            wpa = 2
            wpa_key_mgmt = 'SAE'
            rsn_pairwise = 'CCMP'
            ieee80211w = 2
        elif security_mode == 'WPA2/WPA3':
            wpa = 2
            wpa_key_mgmt = 'WPA-PSK SAE'
            rsn_pairwise = 'CCMP'
            ieee80211w = 1
        else:  # WPA2
            wpa = 2
            wpa_key_mgmt = 'WPA-PSK'
            rsn_pairwise = 'CCMP'
            ieee80211w = 0
        
        config_content = f"""# HaresNet Repeater hostapd configuration
interface={interface}
driver=nl80211
ssid={ssid}
hw_mode=g
channel={channel}
wmm_enabled=1
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid={'1' if hidden else '0'}
wpa={wpa}
wpa_passphrase={password}
wpa_key_mgmt={wpa_key_mgmt}
rsn_pairwise={rsn_pairwise}
ieee80211w={ieee80211w}
"""
        
        try:
            with open(config_path, 'w') as f:
                f.write(config_content)
            return True
        except Exception as e:
            raise Exception(f"Failed to write repeater config: {str(e)}")
    
    def restart(self):
        """Restart hostapd service"""
        try:
            # Kill existing hostapd process
            subprocess.run(['pkill', 'hostapd'], check=False)
            
            import time
            time.sleep(1)
            
            # Start hostapd in background
            subprocess.Popen(['hostapd', '-B', self.config_path])
            return True
        except Exception as e:
            raise Exception(f"Failed to restart hostapd: {str(e)}")

    def disconnect_device(self, mac_address):
        """Force disconnect a device using hostapd_cli"""
        try:
            # Send deauthenticate command
            subprocess.run(
                ['hostapd_cli', '-p', '/var/run/hostapd', 'deauthenticate', mac_address],
                check=False,
                capture_output=True
            )
            # Also try disassociate to be sure
            subprocess.run(
                ['hostapd_cli', '-p', '/var/run/hostapd', 'disassociate', mac_address],
                check=False,
                capture_output=True
            )
            return True
        except Exception as e:
            print(f"Failed to disconnect device {mac_address}: {e}")
            return False
    
    def update_deny_list(self, blocked_macs):
        """Update hostapd deny list with blocked MAC addresses"""
        try:
            # Write blocked MACs to file
            with open(self.deny_path, 'w') as f:
                for mac in blocked_macs:
                    if mac:
                        f.write(f"{mac}\n")
            
            # Reload hostapd configuration
            subprocess.run(['hostapd_cli', 'reload'], check=False)
            
            # Deauthenticate blocked devices
            for mac in blocked_macs:
                if mac:
                    self.disconnect_device(mac)
            
            return True
        except Exception as e:
            print(f"Failed to update deny list: {e}")
            return False

    def get_status(self):
        """Get hostapd service status"""
        try:
            # Check if hostapd process is running using pidof (more robust in container)
            try:
                subprocess.check_call(['pidof', 'hostapd'], stdout=subprocess.DEVNULL)
                is_active = True
            except subprocess.CalledProcessError:
                # Fallback: check if interface is in AP mode
                try:
                    result = subprocess.run(
                        ['iw', 'dev', current_app.config.get('LAN_INTERFACE', 'wlan0'), 'info'],
                        capture_output=True,
                        text=True
                    )
                    is_active = 'type AP' in result.stdout
                except:
                    is_active = False
            
            # Get connected clients count
            clients_count = 0
            try:
                stations_result = subprocess.run(
                    ['iw', 'dev', current_app.config.get('LAN_INTERFACE', 'wlan0'), 'station', 'dump'],
                    capture_output=True,
                    text=True
                )
                clients_count = stations_result.stdout.count('Station')
            except:
                pass
            
            return {
                'active': is_active,
                'clients_connected': clients_count
            }
        except Exception as e:
            return {
                'active': False,
                'error': str(e)
            }
