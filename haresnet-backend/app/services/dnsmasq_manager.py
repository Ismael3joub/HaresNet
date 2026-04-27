import subprocess
from flask import current_app

class DnsmasqManager:
    """Manages dnsmasq DHCP and DNS service"""
    
    def __init__(self):
        self.config_path = '/etc/dnsmasq.conf'
    
    def generate_config(self):
        """Generate dnsmasq configuration"""
        from app.models import RouterConfig
        
        # Get configuration from DB
        config = RouterConfig.query.first()
        
        lan_iface = current_app.config.get('LAN_INTERFACE', 'wlan0')
        
        if config:
            lan_ip = config.lan_ip
            dhcp_start = config.lan_dhcp_start
            dhcp_end = config.lan_dhcp_end
            dhcp_enabled = config.lan_dhcp_enabled
        else:
            lan_ip = current_app.config.get('LAN_IP', '192.168.10.1')
            dhcp_start = current_app.config.get('DHCP_RANGE_START', '192.168.10.100')
            dhcp_end = current_app.config.get('DHCP_RANGE_END', '192.168.10.200')
            dhcp_enabled = True
        
        # Verify LAN Interface exists, if not try to auto-detect
        import os
        if not os.path.exists(f'/sys/class/net/{lan_iface}'):
            current_app.logger.warning(f"Configured interface {lan_iface} not found. Attempting auto-detection.")
            try:
                interfaces = os.listdir('/sys/class/net')
                # Look for wireless interfaces (wl*)
                candidates = [i for i in interfaces if i.startswith('wl') or i.startswith('wlan')]
                
                selected_iface = None
                # Try to find the interface that has the LAN IP
                for candidate in candidates:
                    try:
                        # Check if interface has the expected IP
                        res = subprocess.run(['ip', 'addr', 'show', candidate], capture_output=True, text=True)
                        if f"inet {lan_ip}" in res.stdout:
                            selected_iface = candidate
                            current_app.logger.info(f"Found interface {candidate} matching IP {lan_ip}")
                            break
                    except Exception:
                        continue
                
                if selected_iface:
                    lan_iface = selected_iface
                elif candidates:
                    # Fallback to first candidate if IP match fails
                    lan_iface = candidates[0]
                    current_app.logger.warning(f"Could not match IP {lan_ip}, falling back to {lan_iface}")
                    
            except Exception as e:
                current_app.logger.error(f"Interface detection failed: {e}")

            
        if not dhcp_enabled:
            # Brief config just for DNS if DHCP is disabled
            config_content = f"""# HaresNet dnsmasq configuration (DHCP Disabled)
interface={lan_iface}
bind-interfaces
port=5353
no-dhcp-interface=eth0
domain=haresnet.local
no-resolv
server=8.8.8.8
server=8.8.4.4

# DNS Filter includes
conf-file=/etc/dnsmasq.d/blocklist.conf
conf-file=/etc/dnsmasq.d/allowlist.conf
"""
        else:
            config_content = f"""# HaresNet dnsmasq configuration
# Interface to listen on
interface={lan_iface}
bind-interfaces

# Listen on custom port to allow DNS Proxy on 53
port=5353

# Don't listen on WAN
no-dhcp-interface=eth0

# DHCP range
dhcp-range={dhcp_start},{dhcp_end},12h

# Router advertisement
dhcp-option=3,{lan_ip}

# DNS server
dhcp-option=6,{lan_ip}

# Domain
domain=haresnet.local

# Lease file
dhcp-leasefile=/var/lib/misc/dnsmasq.leases

# DNS settings
no-resolv
server=8.8.8.8
server=8.8.4.4

# Log queries (optional, for debugging)
# log-queries
# log-dhcp

# DNS Filter includes
conf-file=/etc/dnsmasq.d/blocklist.conf
conf-file=/etc/dnsmasq.d/allowlist.conf
"""
        
        try:
            with open(self.config_path, 'w') as f:
                f.write(config_content)
            return True
        except Exception as e:
            raise Exception(f"Failed to write dnsmasq config: {str(e)}")
    
    def restart(self):
        """Restart dnsmasq service (works in Docker and systemd environments)"""
        try:
            # Try systemctl first
            result = subprocess.run(
                ['systemctl', 'restart', 'dnsmasq'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        except Exception:
            pass
        
        # Fallback: pkill + restart (for Docker containers)
        try:
            current_app.logger.info("Restarting dnsmasq via pkill + relaunch...")
            subprocess.run(['pkill', '-x', 'dnsmasq'], capture_output=True, timeout=3)
            import time
            time.sleep(0.5)
            result = subprocess.run(
                ['dnsmasq', '--conf-file=/etc/dnsmasq.conf'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                current_app.logger.info("dnsmasq restarted successfully via pkill")
                return True
            else:
                current_app.logger.warning(f"dnsmasq restart failed: {result.stderr}")
                return False
        except Exception as e:
            current_app.logger.error(f"Error restarting dnsmasq: {str(e)}")
            return False
    
    def get_status(self):
        """Get dnsmasq service status"""
        try:
            # Try systemctl first
            result = subprocess.run(
                ['systemctl', 'is-active', 'dnsmasq'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            return {
                'active': result.stdout.strip() == 'active'
            }
        except Exception as e:
            return {
                'active': False,
                'error': str(e)
            }
