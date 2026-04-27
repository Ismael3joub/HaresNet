
import os
import subprocess
import time
from app import db
from app.models import RouterConfig

class NetworkInterfaceManager:
    """Manages WAN and LAN network interface configurations"""
    
    def __init__(self):
        self.wan_interface = os.environ.get('WAN_INTERFACE', 'eth0')
        self.lan_interface = os.environ.get('LAN_INTERFACE', 'wlan0')
        
    def apply_wan_config(self, config=None):
        """Apply WAN configuration from RouterConfig"""
        if not config:
            config = RouterConfig.query.first()
            
        if not config:
            # Default to DHCP if no config exists
            return self._configure_wan_dhcp()
            
        if config.wan_mode == 'static':
            return self._configure_wan_static(config)
        else:
            return self._configure_wan_dhcp(config)
            
    def apply_lan_config(self, config=None):
        """Apply LAN configuration from RouterConfig"""
        if not config:
            config = RouterConfig.query.first()
            
        if not config:
            # Default configuration if none exists
            lan_ip = os.environ.get('LAN_IP', '192.168.10.1')
            subnet_mask = '255.255.255.0'
        else:
            lan_ip = config.lan_ip
            subnet_mask = config.lan_subnet_mask
            
        try:
            # Calculate CIDR prefix from subnet mask
            cidr = self._netmask_to_cidr(subnet_mask)
            
            # Flush current IP
            subprocess.run(['ip', 'addr', 'flush', 'dev', self.lan_interface], check=False)
            
            # Set new IP
            cmd = ['ip', 'addr', 'add', f'{lan_ip}/{cidr}', 'dev', self.lan_interface]
            subprocess.run(cmd, check=True)
            
            # Ensure interface is up
            subprocess.run(['ip', 'link', 'set', self.lan_interface, 'up'], check=True)
            
            return True, f"LAN configured: {lan_ip}/{cidr}"
        except Exception as e:
            return False, f"Failed to configure LAN: {str(e)}"

    def _configure_wan_dhcp(self, config=None):
        """Configure WAN interface for DHCP"""
        try:
            # Release any static IP configuration
            subprocess.run(['ip', 'addr', 'flush', 'dev', self.wan_interface], check=False)
            
            # Run dhcp client (dhclient or udhcpc depending on system)
            # Try dhclient first, then udhcpc
            if subprocess.run(['which', 'dhclient'], capture_output=True).returncode == 0:
                # Release existing lease
                subprocess.run(['dhclient', '-r', self.wan_interface], check=False)
                # Request new lease
                subprocess.run(['dhclient', self.wan_interface], check=True)
            elif subprocess.run(['which', 'udhcpc'], capture_output=True).returncode == 0:
                subprocess.run(['udhcpc', '-i', self.wan_interface, '-n'], check=True)
            else:
                return False, "No DHCP client found (dhclient or udhcpc)"
                
            return True, "WAN configured for DHCP"
        except Exception as e:
            return False, f"Failed to configure WAN DHCP: {str(e)}"

    def _configure_wan_static(self, config):
        """Configure WAN interface with static IP"""
        try:
            if not config.wan_static_ip:
                return False, "Static IP address is required"
                
            cidr = self._netmask_to_cidr(config.wan_subnet_mask or '255.255.255.0')
            
            # Remove DHCP client if running
            subprocess.run(['pkill', '-f', f'dhclient.*{self.wan_interface}'], check=False)
            subprocess.run(['pkill', '-f', f'udhcpc.*{self.wan_interface}'], check=False)
            
            # Flush current IP
            subprocess.run(['ip', 'addr', 'flush', 'dev', self.wan_interface], check=False)
            
            # Set Static IP
            cmd = ['ip', 'addr', 'add', f'{config.wan_static_ip}/{cidr}', 'dev', self.wan_interface]
            subprocess.run(cmd, check=True)
            
            # Set Gateway
            if config.wan_gateway:
                # Remove existing default route
                subprocess.run(['ip', 'route', 'del', 'default'], check=False)
                # Add new default route
                subprocess.run(['ip', 'route', 'add', 'default', 'via', config.wan_gateway, 'dev', self.wan_interface], check=True)
            
            # Configure DNS
            self._update_dns(config.wan_dns_primary, config.wan_dns_secondary)
            
            return True, f"WAN configured: {config.wan_static_ip}/{cidr}"
        except Exception as e:
            return False, f"Failed to configure WAN Static: {str(e)}"
            
    def _update_dns(self, primary, secondary):
        """Update system DNS resolver"""
        resolv_conf = "/etc/resolv.conf"
        try:
            content = ""
            if primary:
                content += f"nameserver {primary}\n"
            if secondary:
                content += f"nameserver {secondary}\n"
                
            if content:
                with open(resolv_conf, 'w') as f:
                    f.write(content)
        except Exception as e:
            print(f"Failed to update /etc/resolv.conf: {e}")

    def _netmask_to_cidr(self, netmask):
        """Convert subnet mask (e.g. 255.255.255.0) to CIDR (e.g. 24)"""
        try:
            return sum([bin(int(x)).count('1') for x in netmask.split('.')])
        except:
            return 24
