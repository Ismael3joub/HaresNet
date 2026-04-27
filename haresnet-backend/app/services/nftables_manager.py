import subprocess
import json
from flask import current_app

class NftablesManager:
    """Manages nftables firewall rules"""
    
    def __init__(self):
        self.table_name = 'haresnet'
    
    def initialize_firewall(self):
        """Initialize basic firewall rules"""
        wan_iface = current_app.config.get('WAN_INTERFACE', 'eth0')
        lan_iface = current_app.config.get('LAN_INTERFACE', 'wlan0')
        
        rules = f"""
# Flush existing HaresNet table
nft delete table inet {self.table_name} 2>/dev/null || true

# Create table and chains
nft add table inet {self.table_name}
nft add chain inet {self.table_name} input {{ type filter hook input priority 0\\; policy accept\\; }}
nft add chain inet {self.table_name} forward {{ type filter hook forward priority 0\\; policy drop\\; }}
nft add chain inet {self.table_name} output {{ type filter hook output priority 0\\; policy accept\\; }}
# NAT Chains
nft add chain inet {self.table_name} prerouting {{ type nat hook prerouting priority -100\\; policy accept\\; }}
nft add chain inet {self.table_name} postrouting {{ type nat hook postrouting priority 100\\; policy accept\\; }}
nft add chain inet {self.table_name} accounting
nft add chain inet {self.table_name} ip_filter
nft add chain inet {self.table_name} device_blocks
nft add chain inet {self.table_name} service_blocking
nft add chain inet {self.table_name} child_safety


# Jump to device blocking chain (MUST be first to block effectively)
nft add rule inet {self.table_name} forward jump device_blocks

# Jump to service blocking chain
nft add rule inet {self.table_name} forward jump service_blocking

# Jump to accounting chain for forwarded traffic (MUST be second to count all traffic)
nft add rule inet {self.table_name} forward jump accounting

# Jump to IP filter chain
nft add rule inet {self.table_name} forward jump ip_filter

# Jump to child safety chain (NAT prerouting)
nft add rule inet {self.table_name} prerouting jump child_safety

# Force DNS Redirection (DNS Hijacking) - Redirect ALL DNS queries to local proxy
# Except queries from the router itself (implied by prerouting hook usually, but let's be safe: iifname {lan_iface})
nft add rule inet {self.table_name} prerouting iifname {lan_iface} udp dport 53 dnat ip to {current_app.config.get('LAN_IP', '192.168.10.1')}:53
nft add rule inet {self.table_name} prerouting iifname {lan_iface} tcp dport 53 dnat ip to {current_app.config.get('LAN_IP', '192.168.10.1')}:53

# Block QUIC (UDP 443) - Force browsers to use TCP/HTTPS which is easier to inspect/manage
# and prevents DoH over QUIC bypass (mostly)
nft add rule inet {self.table_name} forward udp dport 443 drop

# Block IPv6 DNS Forwarding - Force clients to use IPv4 DNS (which we hijack)
# Since we don't assume we have a working IPv6 DNS Proxy, preventing IPv6 DNS leaks is safer.
nft add rule inet {self.table_name} forward meta nfproto ipv6 udp dport 53 drop
nft add rule inet {self.table_name} forward meta nfproto ipv6 tcp dport 53 drop


# Allow established and related connections
nft add rule inet {self.table_name} forward ct state established,related accept

# Allow forwarding from LAN to WAN
nft add rule inet {self.table_name} forward iifname {lan_iface} oifname {wan_iface} accept

# NAT masquerading for LAN
nft add rule inet {self.table_name} postrouting oifname {wan_iface} masquerade

# Allow loopback
nft add rule inet {self.table_name} input iif lo accept

# Allow SSH (for management)
nft add rule inet {self.table_name} input tcp dport 22 accept

# Allow HTTP/HTTPS for web dashboard
nft add rule inet {self.table_name} input tcp dport 5000 accept
nft add rule inet {self.table_name} input tcp dport 443 accept

# Allow DNS and DHCP
nft add rule inet {self.table_name} input meta nfproto ipv4 udp dport 53 accept
nft add rule inet {self.table_name} input udp dport 67 accept

# Block IPv6 DNS Input (Since we only proxy IPv4)
nft add rule inet {self.table_name} input meta nfproto ipv6 udp dport 53 drop
"""
        
        try:
            subprocess.run(rules, shell=True, check=True)
            return True
        except subprocess.CalledProcessError as e:
            raise Exception(f"Failed to initialize firewall: {str(e)}")
    
    def apply_device_rules(self):
        """Apply per-device blocking rules using batch processing"""
        from app.models import Device
        
        try:
            commands = []
            
            # 1. Create chain if it doesn't exist
            commands.append(f"add chain inet {self.table_name} device_blocks")
            
            # 2. Flush existing rules in the chain
            commands.append(f"flush chain inet {self.table_name} device_blocks")
            
            # 3. Get blocked devices from database
            blocked_devices = Device.query.filter_by(blocked=True).all()
            print(f"[BLOCK] Found {len(blocked_devices)} blocked devices", flush=True)
            
            # 4. Add drop rules for each blocked device
            for device in blocked_devices:
                if device.mac:
                    # Validate MAC format
                    if not self._is_valid_mac(device.mac):
                        print(f"[BLOCK] Skipping invalid MAC: {device.mac}")
                        continue
                    
                    commands.append(f"add rule inet {self.table_name} device_blocks ether saddr {device.mac} drop")
            
            # 5. Ensure jump rule exists in forward chain
            # We can't easily check logic inside a batch for existence without failing the batch if we use 'add rule'
            # But we can use 'insert rule' which might duplicate if we are not careful?
            # actually `initialize_firewall` should have set this up.
            # safe way in batch: check before calling apply_batch, OR just assume it's there from init.
            # Let's check it outside batch to be safe, or just rely on the fact that we ran init.
            
            # To be robust, we check if jump rule exists, if not we add it.
            check_jump = subprocess.run(
                f"nft list chain inet {self.table_name} forward 2>/dev/null | grep -F 'jump device_blocks'",
                shell=True,
                capture_output=True
            )
            
            if check_jump.returncode != 0:
                # Add jump rule
                lan_iface = current_app.config.get('LAN_INTERFACE', 'wlan0')
                commands.append(f"insert rule inet {self.table_name} forward iifname {lan_iface} jump device_blocks")

            # 6. Apply all commands in one batch
            success = self._apply_batch(commands)
            if success:
                 print(f"[BLOCK] Successfully applied blocked device rules")
            return success
            
        except Exception as e:
            print(f"[BLOCK] Error in apply_device_rules: {str(e)}")
            raise
    
    def apply_schedule_rule(self, device_mac, action):
        """Apply or remove schedule-based rule for a device"""
        # If app config requests a dry-run, don't call system nft commands
        try:
            if current_app and current_app.config.get('DRY_RUN_NFT', False):
                print(f"[DRY RUN] {action} rule for {device_mac}")
                return True
        except Exception:
            pass
        
        # Validate MAC address format
        if not device_mac or not self._is_valid_mac(device_mac):
            print(f"Invalid MAC address: {device_mac}")
            return False

        if action == 'block':
            # Block by MAC address - drop traffic from this device
            # Use both source and destination MAC for completeness
            cmd = f"nft add rule inet {self.table_name} forward ether saddr {device_mac} drop"
            try:
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    print(f"Successfully blocked {device_mac}")
                    return True
                else:
                    # Check if rule already exists
                    check = subprocess.run(
                        f"nft list chain inet {self.table_name} forward | grep -F '{device_mac}'",
                        shell=True,
                        capture_output=True,
                        timeout=5
                    )
                    if check.returncode == 0:
                        print(f"Rule for {device_mac} already exists")
                        return True
                    print(f"Failed to block {device_mac}: {result.stderr}")
                    return False
            except Exception as e:
                print(f"Exception while blocking {device_mac}: {str(e)}")
                return False
        
        else:  # allow
            # Remove block rule for this device
            cmd = f"nft delete rule inet {self.table_name} forward ether saddr {device_mac} drop"
            try:
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    print(f"Successfully unblocked {device_mac}")
                    return True
                else:
                    # Check if rule exists before trying to delete
                    check = subprocess.run(
                        f"nft list chain inet {self.table_name} forward | grep -F '{device_mac}'",
                        shell=True,
                        capture_output=True,
                        timeout=5
                    )
                    if check.returncode != 0:
                        print(f"No rule found for {device_mac}, nothing to unblock")
                        return True
                    print(f"Failed to unblock {device_mac}: {result.stderr}")
                    return False
            except Exception as e:
                print(f"Exception while unblocking {device_mac}: {str(e)}")
                return False
    
    @staticmethod
    def _is_valid_mac(mac):
        """Validate MAC address format"""
        import re
        mac_pattern = r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$'
        return re.match(mac_pattern, mac) is not None
    
    def get_current_rules(self):
        """Get currently active nftables rules"""
        try:
            result = subprocess.run(
                f"nft list table inet {self.table_name}",
                shell=True,
                capture_output=True,
                text=True,
                check=True
            )
            # Return rules as a list of non-empty lines for easy consumption by clients
            lines = [ln for ln in result.stdout.splitlines() if ln.strip()]
            return lines
        except subprocess.CalledProcessError:
            return []
    
    def get_status(self):
        """Get firewall status"""
        try:
            result = subprocess.run(
                f"nft list table inet {self.table_name}",
                shell=True,
                capture_output=True,
                text=True
            )
            return {
                'active': result.returncode == 0,
                'table': self.table_name
            }
        except Exception as e:
            return {
                'active': False,
                'error': str(e)
            }
            
    def clear_conntrack(self, ip_address):
        """Clear connection tracking entries for a specific IP"""
        if not ip_address:
            return
            
        try:
            # Check if conntrack is available
            check = subprocess.run(['which', 'conntrack'], capture_output=True)
            if check.returncode != 0:
                print(f"[CONNTRACK] Warning: 'conntrack' utility not found. Active connections for {ip_address} will not be cleared.")
                return

            # Delete entries where source is the IP
            # We use text=True to capture output as string if needed for debug
            res_s = subprocess.run(
                f"conntrack -D -s {ip_address}", 
                shell=True, 
                capture_output=True,
                text=True
            )
            
            # Delete entries where destination is the IP
            res_d = subprocess.run(
                f"conntrack -D -d {ip_address}", 
                shell=True, 
                capture_output=True,
                text=True
            )
            
            if res_s.returncode != 0 and "0 flow entries have been deleted" not in res_s.stderr:
                 print(f"[CONNTRACK] Notice: Failed to clear source entries for {ip_address}: {res_s.stderr.strip()}")
            
            if res_d.returncode != 0 and "0 flow entries have been deleted" not in res_d.stderr:
                 print(f"[CONNTRACK] Notice: Failed to clear dest entries for {ip_address}: {res_d.stderr.strip()}")
                 
            print(f"[CONNTRACK] Cleared connections for {ip_address}")
            
        except Exception as e:
            print(f"[CONNTRACK] Failed to clear connections for {ip_address}: {e}")



    def apply_service_blocking_rules(self):
        """Apply service blocking rules using sets"""
        from app.models import Service, Device
        
        # Respect dry run configuration
        if current_app and current_app.config.get('DRY_RUN_NFT', False):
            print(f"[DRY RUN] Would apply service blocking rules")
            return True

        try:
            # Initialize sets (ensure blocked_dns_v4/v6 exist)
            self.initialize_sets()

            # Create chain
            subprocess.run(f"nft add chain inet {self.table_name} service_blocking", shell=True, check=False)
            subprocess.run(f"nft flush chain inet {self.table_name} service_blocking", shell=True, check=False)
            
            # Ensure jump rule exists in forward chain
            check_jump = subprocess.run(
                f"nft list chain inet {self.table_name} forward | grep -F 'jump service_blocking'",
                shell=True, capture_output=True
            )
            if check_jump.returncode != 0:
                # Insert after device_blocks (which is usually first)
                # We can just append to forward chain, but priority matters.
                # initialize_firewall adds it. If it's missing, let's append.
                subprocess.run(f"nft add rule inet {self.table_name} forward jump service_blocking", shell=True)

            # Get all services and their IPs
            services = Service.query.filter_by(enabled=True).all()
            
            for service in services:
                if not service.ips:
                    continue
                
                # --- IPv4 Set ---
                set_name_v4 = f"service_{service.id}_v4"
                # Quote the definition to protect semicolons from shell
                subprocess.run(f"nft add set inet {self.table_name} {set_name_v4} '{{ type ipv4_addr; flags interval; }}'", shell=True, check=False)
                subprocess.run(f"nft flush set inet {self.table_name} {set_name_v4}", shell=True, check=False)
                
                # --- IPv6 Set ---
                set_name_v6 = f"service_{service.id}_v6"
                subprocess.run(f"nft add set inet {self.table_name} {set_name_v6} '{{ type ipv6_addr; flags interval; }}'", shell=True, check=False)
                subprocess.run(f"nft flush set inet {self.table_name} {set_name_v6}", shell=True, check=False)
                
                # Add IPs to sets
                elements_v4 = []
                elements_v6 = []
                
                for service_ip in service.ips:
                    if ':' in service_ip.cidr:
                        elements_v6.append(service_ip.cidr)
                    else:
                        elements_v4.append(service_ip.cidr)
                
                if elements_v4:
                    elems_str = ", ".join(elements_v4)
                    # Quote elements
                    cmd = f"nft add element inet {self.table_name} {set_name_v4} '{{ {elems_str} }}'"
                    subprocess.run(cmd, shell=True, check=False)
                    
                if elements_v6:
                    elems_str = ", ".join(elements_v6)
                    cmd = f"nft add element inet {self.table_name} {set_name_v6} '{{ {elems_str} }}'"
                    subprocess.run(cmd, shell=True, check=False)

            # Apply drop rules for blocked devices
            devices = Device.query.all()
            for device in devices:
                if not device.blocked_services:
                    continue
                    
                if not device.mac or not self._is_valid_mac(device.mac):
                    continue
                
                # --- ANTI-BYPASS: Block DoT/DoH for these devices too ---
                # Identical to child safety rules, ensures they can't bypass the DNS block via 8.8.8.8
                # Block DoT (853)
                subprocess.run(f"nft add rule inet {self.table_name} service_blocking ether saddr {device.mac} meta nfproto ipv4 tcp dport 853 drop", shell=True, check=False)
                subprocess.run(f"nft add rule inet {self.table_name} service_blocking ether saddr {device.mac} meta nfproto ipv4 udp dport 853 drop", shell=True, check=False)
                
                # Block DoH to known providers (Port 443)
                subprocess.run(f"nft add rule inet {self.table_name} service_blocking ether saddr {device.mac} ip daddr @blocked_dns_v4 tcp dport 443 drop", shell=True, check=False)
                subprocess.run(f"nft add rule inet {self.table_name} service_blocking ether saddr {device.mac} ip6 daddr @blocked_dns_v6 tcp dport 443 drop", shell=True, check=False)
                
                for service in device.blocked_services:
                    # Block IPv4
                    set_name_v4 = f"service_{service.id}_v4"
                    cmd_v4 = f"nft add rule inet {self.table_name} service_blocking ether saddr {device.mac} ip daddr @{set_name_v4} drop"
                    subprocess.run(cmd_v4, shell=True, check=False)
                    
                    # Block IPv6
                    set_name_v6 = f"service_{service.id}_v6"
                    cmd_v6 = f"nft add rule inet {self.table_name} service_blocking ether saddr {device.mac} ip6 daddr @{set_name_v6} drop"
                    subprocess.run(cmd_v6, shell=True, check=False)
                    
            return True
        except Exception as e:
            print(f"[SERVICE-BLOCK] Error: {e}")
            return False

    def _apply_batch(self, commands):
        """Apply a list of nftables commands in a single batch transaction"""
        if not commands:
            return True
            
        try:
            # Create a temporary file with the script
            # We wrap everything in a transaction for atomicity
            script_content = "table inet " + self.table_name + " {\n"
            
            # Since we are inside the table block, commands shouldn't repeat 'nft add rule inet table ...'
            # Instead they should be like 'chain chain_name { ... }' or 'add rule chain_name ...'
            # However, simpler approach for now to avoid parsing: just flush and run commands sequentially in a file
            # But 'nft -f' expects a certain format.
            
            # Better approach: Just write the full commands to a file and run 'nft -f'
            # BUT: nft -f expects a syntax like 'add rule inet table chain ...' or a structured config.
            # AND: standard 'nft -f' is atomic only if the file is a complete ruleset or valid transaction.
            
            # Let's use the standard "nft -f -" input method with full commands
            # We just need to make sure we don't use 'nft' prefix in the file if using 'nft -f' with specific syntax?
            # Actually, standard way is to pipe content to 'nft -f -'
            
            full_script = "\n".join(commands)
            
            if current_app and current_app.config.get('DRY_RUN_NFT', False):
                print(f"[DRY RUN BATCH] Would run:\n{full_script}")
                return True
                
            process = subprocess.Popen(
                ['nft', '-f', '-'],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = process.communicate(input=full_script)
            
            if process.returncode != 0:
                print(f"[NFT-BATCH] Error applying batch: {stderr}")
                print(f"[NFT-BATCH] Failed script:\n{full_script}")
                return False
                
            return True
        except Exception as e:
            print(f"[NFT-BATCH] Exception: {str(e)}")
            return False

    def initialize_sets(self, commands=None):
        """Initialize named sets for blocking. If commands is provided, append instead of applying."""
        execute_now = commands is None
        if commands is None:
            commands = []
            
        # We need these sets to exist for child safety
        commands.extend([
            f"add set inet {self.table_name} blocked_dns_v4 {{ type ipv4_addr; flags interval; }}",
            f"add set inet {self.table_name} blocked_dns_v6 {{ type ipv6_addr; flags interval; }}",
            f"add set inet {self.table_name} child_safe_devices {{ type ether_addr; }}"
        ])
        
        # Populate the DNS sets with known bad providers (DoH/DoT)
        # This only needs to be done once or when updated
        KNOWN_DNS_V4 = [
            "8.8.8.8", "8.8.4.4", # Google
            "1.1.1.1", "1.0.0.1", # Cloudflare
            "9.9.9.9", "149.112.112.112", # Quad9
            "208.67.222.222", "208.67.220.220", # OpenDNS
            "94.140.14.14", "94.140.15.15" # AdGuard
        ]
        
        KNOWN_DNS_V6 = [
            "2001:4860:4860::8888", "2001:4860:4860::8844",
            "2606:4700:4700::1111", "2606:4700:4700::1001",
            "2620:fe::fe", "2620:fe::9",
            "2620:119:35::35", "2620:119:53::53",
            "2a10:50c0::ad1:ff", "2a10:50c0::ad2:ff"
        ]
        
        # Flush sets first
        commands.extend([
            f"flush set inet {self.table_name} blocked_dns_v4",
            f"flush set inet {self.table_name} blocked_dns_v6"
        ])
        
        # Add elements
        if KNOWN_DNS_V4:
            elems = ", ".join(KNOWN_DNS_V4)
            commands.append(f"add element inet {self.table_name} blocked_dns_v4 {{ {elems} }}")
            
        if KNOWN_DNS_V6:
            elems = ", ".join(KNOWN_DNS_V6)
            commands.append(f"add element inet {self.table_name} blocked_dns_v6 {{ {elems} }}")
            
        if execute_now:
            self._apply_batch(commands)

    def clear_conntrack_batch(self, ips):
        """Clear connection tracking for multiple IPs in one go"""
        if not ips:
            return

        try:
            # Check if conntrack is available (once)
            check = subprocess.run(['which', 'conntrack'], capture_output=True)
            if check.returncode != 0:
                print(f"[CONNTRACK] Warning: 'conntrack' utility not found.", flush=True)
                return

            # Build a single shell script to run all commands
            # This avoids spawning a subprocess for every single IP
            cmds = []
            for ip in ips:
                cmds.append(f"conntrack -D -s {ip} >/dev/null 2>&1")
                cmds.append(f"conntrack -D -d {ip} >/dev/null 2>&1")
            
            full_cmd = "; ".join(cmds)
            
            # Run in a single shell
            subprocess.run(full_cmd, shell=True)
            print(f"[CONNTRACK] cleared connections for {len(ips)} devices", flush=True)

        except Exception as e:
            print(f"[CONNTRACK] Batch clear failed: {e}", flush=True)

    def apply_child_safety_rules(self):
        """Apply DNS filtering rules for child-safe devices using batch execution"""
        from app.models import Device
        
        try:
            commands = []
            
            # 0. Initialize sets directly into the command batch
            self.initialize_sets(commands)
            
            # 1. Ensure chains exist
            # Prerouting (NAT)
            commands.append(f"add chain inet {self.table_name} prerouting {{ type nat hook prerouting priority -100; policy accept; }}")
            # Child Safety Chain
            commands.append(f"add chain inet {self.table_name} child_safety")
            # Flush Child Safety
            commands.append(f"flush chain inet {self.table_name} child_safety")
            
            # 2. Get Devices
            child_devices = Device.query.filter_by(child_safe=True).all()
            print(f"[CHILD-SAFETY] Found {len(child_devices)} child-safe devices", flush=True)
            
            # Collect IPs to clear conntrack
            ips_to_clear = []

            # 3. Build Rules
            for device in child_devices:
                # Collect IP for batch clearing
                if device.ip:
                    # heuristic: only clear if seen recently
                    if device.last_seen:
                         from datetime import datetime
                         diff = (datetime.utcnow() - device.last_seen).total_seconds()
                         if diff < 120: # 2 minutes
                             ips_to_clear.append(device.ip)
                
                if device.mac and self._is_valid_mac(device.mac):
                    mac = device.mac
                    
                    # A. DNS Redirection (Port 53) -> Cloudflare Family
                    commands.append(f"add rule inet {self.table_name} child_safety ether saddr {mac} meta nfproto ipv4 udp dport 53 dnat to 1.1.1.3")
                    commands.append(f"add rule inet {self.table_name} child_safety ether saddr {mac} meta nfproto ipv4 tcp dport 53 dnat to 1.1.1.3")
                    commands.append(f"add rule inet {self.table_name} child_safety ether saddr {mac} meta nfproto ipv6 udp dport 53 dnat to [2606:4700:4700::1113]")
                    commands.append(f"add rule inet {self.table_name} child_safety ether saddr {mac} meta nfproto ipv6 tcp dport 53 dnat to [2606:4700:4700::1113]")
                    
                    # B. Block DoT (Port 853)
                    commands.append(f"add rule inet {self.table_name} child_safety ether saddr {mac} meta nfproto ipv4 tcp dport 853 drop")
                    commands.append(f"add rule inet {self.table_name} child_safety ether saddr {mac} meta nfproto ipv4 udp dport 853 drop")
                    
                    # C. Block DoH/DoT to known providers (Port 443) using named sets
                    commands.append(f"add rule inet {self.table_name} child_safety ether saddr {mac} ip daddr @blocked_dns_v4 tcp dport 443 drop")
                    commands.append(f"add rule inet {self.table_name} child_safety ether saddr {mac} ip6 daddr @blocked_dns_v6 tcp dport 443 drop")

            # 4. Add jump rule if not present
            check_jump = subprocess.run(
                f"nft list chain inet {self.table_name} prerouting | grep -F 'jump child_safety'",
                shell=True, capture_output=True
            )
            if check_jump.returncode != 0:
                commands.append(f"add rule inet {self.table_name} prerouting jump child_safety")

            # 5. Apply the entire batch
            result = self._apply_batch(commands)
            
            # 6. batch clear conntrack (only if batch application was successful? actually better to do it anyway)
            if ips_to_clear:
                 self.clear_conntrack_batch(ips_to_clear)
                 
            return result
                
        except Exception as e:
            print(f"[CHILD-SAFETY] Error applying rules: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    def add_accounting_rule(self, ip_address):
        """Add traffic accounting rules for an IP"""
        # Add to accounting chain
        # Check if rule exists first to avoid duplicates?
        # A simple grep check works.
        try:
            check = subprocess.run(
                f"nft list chain inet {self.table_name} accounting | grep '{ip_address}'",
                shell=True,
                capture_output=True
            )
            if check.returncode == 0:
                return True # Already exists

            # Upload: Source is IP
            cmd_up = f"nft add rule inet {self.table_name} accounting ip saddr {ip_address} counter"
            subprocess.run(cmd_up, shell=True, check=True)
            
            # Download: Destination is IP
            cmd_down = f"nft add rule inet {self.table_name} accounting ip daddr {ip_address} counter"
            subprocess.run(cmd_down, shell=True, check=True)
            return True
        except subprocess.CalledProcessError:
            return False

    def get_counters(self):
        """Get all counters from nftables"""
        try:
            # We parse text output because JSON support varies by version
            result = subprocess.run(
                ['nft', 'list', 'chain', 'inet', self.table_name, 'accounting'],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                return {}

            counters = {} # ip -> {rx: bytes, tx: bytes}
            
            # Example output:
            # ip saddr 192.168.10.10 counter packets 500 bytes 45000
            # ip daddr 192.168.10.10 counter packets 800 bytes 900000
            
            lines = result.stdout.splitlines()
            for line in lines:
                parts = line.strip().split()
                if 'counter' not in parts: continue
                
                try:
                    bytes_idx = parts.index('bytes')
                    bytes_val = int(parts[bytes_idx + 1])
                    
                    if 'saddr' in parts:
                        ip_idx = parts.index('saddr')
                        ip = parts[ip_idx + 1]
                        if ip not in counters: counters[ip] = {'rx': 0, 'tx': 0}
                        counters[ip]['tx'] = bytes_val
                    elif 'daddr' in parts:
                        ip_idx = parts.index('daddr')
                        ip = parts[ip_idx + 1]
                        if ip not in counters: counters[ip] = {'rx': 0, 'tx': 0}
                        counters[ip]['rx'] = bytes_val
                except (ValueError, IndexError):
                    continue
                    
            return counters
            
        except Exception as e:
            print(f"Error parsing counters: {e}")
            return {}

    def apply_ip_filter_rules(self):
        """Apply IP/Port filtering rules"""
        from app.models import IPFilterRule, SystemSettings
        
        try:
            # 1. Check if enabled globally
            setting = SystemSettings.query.filter_by(key='ip_filter_enabled').first()
            if not setting or setting.value != 'true':
                # Disabled -> Flush chain and return
                self._apply_batch([
                    f"flush chain inet {self.table_name} ip_filter"
                ])
                return True
                
            # 2. Get Rules
            rules = IPFilterRule.query.filter_by(enabled=True).all()
            whitelist_rules = [r for r in rules if r.list_type == 'whitelist']
            blacklist_rules = [r for r in rules if r.list_type == 'blacklist']
            
            commands = [f"flush chain inet {self.table_name} ip_filter"]
            
            # 3. Determine Mode
            # "When white list is not empty, white list works instead of black list."
            if whitelist_rules:
                # Whitelist Mode
                for rule in whitelist_rules:
                    rule_cmds = self._build_rule_cmds(rule)
                    for cmd in rule_cmds:
                        commands.append(f"add rule inet {self.table_name} ip_filter {cmd} accept")
                
                # Default policy for Whitelist mode: Drop everything else
                commands.append(f"add rule inet {self.table_name} ip_filter drop")
                
            else:
                # Blacklist Mode
                for rule in blacklist_rules:
                    rule_cmds = self._build_rule_cmds(rule)
                    for cmd in rule_cmds:
                        commands.append(f"add rule inet {self.table_name} ip_filter {cmd} drop")
                
            self._apply_batch(commands)
            return True
            
        except Exception as e:
            print(f"[IP-FILTER] Error applying rules: {str(e)}")
            return False

    def _build_rule_cmds(self, rule):
        """Build nftables match commands from rule"""
        base_parts = []
        
        # IP Version
        if rule.ip_version == 6:
            base_parts.append("ip6")
        else:
            base_parts.append("ip")
            
        # Source/Dest IP
        if rule.source_ip:
            base_parts.append(f"saddr {rule.source_ip}")
        if rule.dest_ip:
            base_parts.append(f"daddr {rule.dest_ip}")

        # Protocol & Ports
        proto = rule.protocol.lower() if rule.protocol else 'all'
        cmds = []
        
        if proto == 'all':
            # Handle cases where ports are specified with 'all' (implying TCP+UDP)
            if rule.source_port or rule.dest_port:
                # Generate matching for TCP
                tcp_parts = base_parts + ["tcp"]
                if rule.source_port: tcp_parts.append(f"sport {rule.source_port}")
                if rule.dest_port: tcp_parts.append(f"dport {rule.dest_port}")
                cmds.append(" ".join(tcp_parts))
                
                # Generate matching for UDP
                udp_parts = base_parts + ["udp"]
                if rule.source_port: udp_parts.append(f"sport {rule.source_port}")
                if rule.dest_port: udp_parts.append(f"dport {rule.dest_port}")
                cmds.append(" ".join(udp_parts))
            else:
                # Just IP matching
                cmds.append(" ".join(base_parts))
                
        elif proto in ['tcp', 'udp']:
            parts = base_parts + [proto]
            if rule.source_port: parts.append(f"sport {rule.source_port}")
            if rule.dest_port: parts.append(f"dport {rule.dest_port}")
            cmds.append(" ".join(parts))
            
        elif proto == 'icmp':
            if rule.ip_version == 6:
                parts = base_parts + ["nexthdr icmpv6"]
            else:
                parts = base_parts + ["protocol icmp"]
            cmds.append(" ".join(parts))
            
        return cmds
