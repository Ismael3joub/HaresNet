import ipaddress
from app import db
from app.models import Service, ServiceIP, Device, User
from flask import current_app

class ServiceManager:
    """Manages blocked services and their IP ranges"""
    
    INITIAL_SERVICES = {
        'instagram': {
            'label': 'Instagram',
            'icon': 'instagram',
            'ips': [
                '157.240.0.0/16', '157.240.1.0/24', # Meta
                '31.13.64.0/18', '69.63.176.0/20'
            ]
        },
        'snapchat': {
            'label': 'Snapchat', 
            'icon': 'snapchat',
            'ips': [
                '104.193.184.0/22', '35.184.0.0/13' # GCP/Snap keys - unreliable but better than nothing
            ]
        },
        'tiktok': {
            'label': 'TikTok',
            'icon': 'tiktok',
            'ips': [
                '161.117.0.0/16', '161.117.1.0/24' # ByteDance
            ]
        },
        'whatsapp': {
            'label': 'WhatsApp',
            'icon': 'whatsapp',
            'ips': [
                '157.240.0.0/16' # Meta
            ]
        },
        'facebook': {
            'label': 'Facebook',
            'icon': 'facebook',
            'ips': [
                '157.240.0.0/16', '31.13.64.0/18'
            ]
        }
    }
    
    def initialize_services(self):
        """Seed initial services if they don't exist"""
        try:
            # Only seed if no services exist to avoid recreating deleted ones
            if Service.query.count() > 0:
                return

            print("No services found. Seeding initial services...")
            for name, data in self.INITIAL_SERVICES.items():
                service = Service(
                    name=name,
                    label=data['label'],
                    icon=data['icon'],
                    enabled=True
                )
                db.session.add(service)
                db.session.flush()
                
                # Add initial IPs
                for cidr in data['ips']:
                    try:
                        ipaddress.ip_network(cidr)
                        ip = ServiceIP(service_id=service.id, cidr=cidr)
                        db.session.add(ip)
                    except ValueError:
                        continue
            
            db.session.commit()
            print("Initial services seeded.")
        except Exception as e:
            db.session.rollback()
            print(f"Error initializing services: {e}")

    def get_service_count(self):
        """Get number of seeded services"""
        try:
            return Service.query.count()
        except:
            return 0

    def get_services(self):
        """Get all available services"""
        return Service.query.all()
        
    def toggle_service_for_device(self, device_id, service_id, blocked):
        """Block or unblock a service for a device"""
        device = Device.query.get(device_id)
        service = Service.query.get(service_id)
        
        if not device or not service:
            return False, "Device or Service not found"
            
        if blocked:
            if service not in device.blocked_services:
                device.blocked_services.append(service)
        else:
            if service in device.blocked_services:
                device.blocked_services.remove(service)
                
        try:
            db.session.commit()
            
            # Apply firewall rules immediately
            from app.services.nftables_manager import NftablesManager
            nm = NftablesManager()
            nm.apply_service_blocking_rules()
            
            # --- INSTANT ENFORCEMENT ---
            # Clear conntrack and disconnect device to force DNS flush and drop active connections
            if device.ip or device.mac:
                try:
                    print(f"[SERVICE-BLOCK] Enforcing rules for {device.label}...", flush=True)
                    if device.ip:
                        nm.clear_conntrack(device.ip)
                    
                    if device.mac:
                        from app.services.hostapd_manager import HostapdManager
                        HostapdManager().disconnect_device(device.mac)
                except Exception as e:
                    print(f"[SERVICE-BLOCK] Enforcement warning: {e}", flush=True)
            # ---------------------------

            return True, "Updated successfully"
        except Exception as e:
            db.session.rollback()
            return False, str(e)

    def add_service_ip(self, service_id, cidr):
        """Add a single IP/CIDR to a service"""
        try:
            # Validate
            ipaddress.ip_network(cidr)
        except ValueError:
            return False, "Invalid CIDR format"
            
        service = Service.query.get(service_id)
        if not service:
            return False, "Service not found"
            
        # Check if exists
        exists = ServiceIP.query.filter_by(service_id=service_id, cidr=cidr).first()
        if exists:
            return True, "CIDR already exists"
            
        try:
            new_ip = ServiceIP(service_id=service_id, cidr=cidr)
            db.session.add(new_ip)
            db.session.commit()
            
            # Re-apply firewall rules
            from app.services.nftables_manager import NftablesManager
            nm = NftablesManager()
            nm.apply_service_blocking_rules()
            
            return True, "IP range added"
        except Exception as e:
            db.session.rollback()
            return False, str(e)

    def remove_service_ip(self, service_id, cidr):
        """Remove a single IP/CIDR from a service"""
        service_ip = ServiceIP.query.filter_by(service_id=service_id, cidr=cidr).first()
        if not service_ip:
            return False, "IP range not found"
            
        try:
            db.session.delete(service_ip)
            db.session.commit()
            
            # Re-apply firewall rules
            from app.services.nftables_manager import NftablesManager
            nm = NftablesManager()
            nm.apply_service_blocking_rules()
            
            return True, "IP range removed"
        except Exception as e:
            db.session.rollback()
            return False, str(e)

    def create_service(self, name, label, icon=None, domain=None):
        """Create a new custom service"""
        if not domain:
            return None, "Domain is required"

        # Check name uniqueness
        if Service.query.filter_by(name=name).first():
            return None, "Service name already exists"

        try:
            service = Service(
                name=name,
                label=label,
                icon=icon or 'globe',
                domain=domain,
                enabled=True
            )
            db.session.add(service)
            db.session.flush() # Get ID
            
            # Resolve domain
            self.refresh_service_ips(service)
            
            db.session.commit()
            return service, "Service created successfully"
        except Exception as e:
            db.session.rollback()
            return None, f"Failed to create service: {str(e)}"

    def refresh_service_ips(self, service):
        """Resolve domain and update IPs for a service"""
        if not service.domain:
            return
            
        import socket
        try:
            # Clean domain
            domain = service.domain.lower().replace('https://', '').replace('http://', '').split('/')[0]
            
            domains_to_resolve = [domain]
            if not domain.startswith('www.'):
                domains_to_resolve.append(f"www.{domain}")
            
            new_ips = set()
            

            for d in domains_to_resolve:
                # Try both IPv4 and IPv6
                for family in [socket.AF_INET, socket.AF_INET6]:
                    try:
                        # Resolve
                        infos = socket.getaddrinfo(d, 80, family, socket.SOCK_STREAM)
                        for info in infos:
                            ip_addr = info[4][0]
                             # Scope ID handling for IPv6 (remove %eth0 etc if present)
                            if '%' in ip_addr:
                                ip_addr = ip_addr.split('%')[0]
                            new_ips.add(ip_addr)
                    except Exception as e:
                        # It's normal for one family to fail if not configured
                        pass

                
            # Update DB
            # Get current IPs
            current_ips = {ip.cidr for ip in service.ips}
            
            # Add new ones
            for ip_str in new_ips:
                if ip_str not in current_ips:
                    try:
                        # Validate and add
                        ipaddress.ip_network(ip_str)
                        new_ip = ServiceIP(service_id=service.id, cidr=ip_str)
                        db.session.add(new_ip)
                    except ValueError:
                        pass
            
            # We don't remove old IPs automatically right now to be safe, 
            # or we could if we want to track dynamic DNS changes strictly.
            # User asked for "dynamic update", implying we should follow DNS.
            # Let's remove IPs that are no longer returned? 
            # Risk: DNS might return a subset (round-robin).
            # Better to keep them for a while? 
            # For this MVP, let's just ADD new ones.
            
        except Exception as e:
            print(f"Failed to refresh IPs for {service.name}: {e}")

    def delete_service(self, service_id):
        """Delete a service"""
        service = Service.query.get(service_id)
        if not service:
            return False, "Service not found"
            
        try:
            # ServiceIPs will be deleted by cascade
            # Default blocked_services relationships will also be handled by association table deletion
            
            # However, we need to clear nftables rules FIRST before deleting from DB, 
            # otherwise we might leave stale sets or rules if we rely on DB state.
            # But apply_rules relies on DB state. 
            # So actual workflow: 
            # 1. Delete from DB. 
            # 2. Re-apply rules (which reads from DB, so it won't see this service/devices anymore).
            
            db.session.delete(service)
            db.session.commit()
            
            # Re-apply firewall rules
            from app.services.nftables_manager import NftablesManager
            nm = NftablesManager()
            nm.apply_service_blocking_rules()
            
            return True, "Service deleted"
        except Exception as e:
            db.session.rollback()
            return False, str(e)

    def update_blocked_devices(self, service_id, device_ids):
        """Update the list of devices blocking this service"""
        service = Service.query.get(service_id)
        if not service:
            return False, "Service not found"
            
        try:
            # Clear current devices
            service.devices = []
            
            # Add new devices
            if device_ids:
                devices = Device.query.filter(Device.id.in_(device_ids)).all()
                service.devices.extend(devices)
            
            db.session.commit()
            
            # Re-apply firewall rules
            from app.services.nftables_manager import NftablesManager
            nm = NftablesManager()
            nm.apply_service_blocking_rules()
            
            # --- INSTANT ENFORCEMENT ---
            # Kick all affected devices
            if device_ids:
                try:
                    devices = Device.query.filter(Device.id.in_(device_ids)).all()
                    from app.services.hostapd_manager import HostapdManager
                    hm = HostapdManager()
                    for dev in devices:
                        if dev.ip:
                            nm.clear_conntrack(dev.ip)
                        if dev.mac:
                            hm.disconnect_device(dev.mac)
                except Exception as e:
                    print(f"[SERVICE-BLOCK] Bulk enforcement warning: {e}", flush=True)
            # ---------------------------
            
            return True, "Blocked devices updated"
        except Exception as e:
            db.session.rollback()
            return False, str(e)
