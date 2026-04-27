from datetime import datetime
from app import db
import bcrypt

class User(db.Model):
    """Admin user model"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    otp_code = db.Column(db.String(6))
    otp_expires_at = db.Column(db.DateTime)
    reset_token = db.Column(db.String(6))
    reset_token_expires_at = db.Column(db.DateTime)
    
    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def check_password(self, password):
        """Check password against hash"""
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'created_at': self.created_at.isoformat()
        }


class Device(db.Model):
    """Connected device model"""
    id = db.Column(db.Integer, primary_key=True)
    mac = db.Column(db.String(17), unique=True, nullable=False, index=True)
    ip = db.Column(db.String(15))
    hostname = db.Column(db.String(255))
    vendor = db.Column(db.String(255))
    label = db.Column(db.String(100))
    group = db.Column(db.String(50))
    blocked = db.Column(db.Boolean, default=False)
    child_safe = db.Column(db.Boolean, default=False)
    first_seen = db.Column(db.DateTime, default=datetime.utcnow)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Traffic Limits (in MB)
    traffic_limit_daily_mb = db.Column(db.Integer, default=0) # 0 = no limit
    traffic_limit_hourly_mb = db.Column(db.Integer, default=0) # 0 = no limit
    alert_sent_at = db.Column(db.DateTime) # Timestamp of last alert sent
    
    schedules = db.relationship('Schedule', backref='device', lazy=True, cascade='all, delete-orphan')
    blocked_services = db.relationship('Service', secondary='device_blocked_services', lazy='subquery',
        backref=db.backref('devices', lazy=True))
    
    def to_dict(self):
        # Calculate online status dynamically
        # Threshold: 2 seconds
        is_online = False
        if self.last_seen:
            diff = (datetime.utcnow() - self.last_seen).total_seconds()
            # Threshold: 8 seconds (must be > 3x scheduler interval of 2s)
            is_online = diff < 8

        return {
            'id': self.id,
            'mac': self.mac,
            'ip': self.ip,
            'hostname': self.hostname,
            'vendor': self.vendor,
            'label': self.label,
            'group': self.group,
            'blocked': self.blocked,
            'first_seen': self.first_seen.isoformat(),
            'last_seen': self.last_seen.isoformat(),
            'is_online': is_online,
            'child_safe': self.child_safe,
            'traffic_limit_daily_mb': self.traffic_limit_daily_mb,
            'traffic_limit_hourly_mb': self.traffic_limit_hourly_mb,
            'blocked_services': [s.id for s in self.blocked_services]
        }

class Schedule(db.Model):
    """Time-based access control schedule"""
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.Integer, db.ForeignKey('device.id'), nullable=False)
    name = db.Column(db.String(100))
    days = db.Column(db.String(50))  # JSON string: ["monday", "tuesday", ...]
    start_time = db.Column(db.String(5))  # HH:MM format
    end_time = db.Column(db.String(5))    # HH:MM format
    action = db.Column(db.String(10))     # "block" or "allow"
    enabled = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        import json
        try:
            days_list = json.loads(self.days) if self.days else []
        except:
            days_list = []
            
        return {
            'id': self.id,
            'device_id': self.device_id,
            'name': self.name,
            'days': days_list,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'action': self.action,
            'enabled': self.enabled,
            'created_at': self.created_at.isoformat()
        }

class WiFiConfig(db.Model):
    """Wi-Fi access point configuration"""
    id = db.Column(db.Integer, primary_key=True)
    ssid = db.Column(db.String(32), nullable=False)
    password = db.Column(db.String(64))
    security_mode = db.Column(db.String(20), default='WPA2')  # WPA2, WPA3, WPA2/WPA3
    band = db.Column(db.String(10), default='2.4GHz')  # '2.4GHz', '5GHz'
    channel = db.Column(db.Integer, default=6)
    hidden = db.Column(db.Boolean, default=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'ssid': self.ssid,
            'security_mode': self.security_mode,
            'band': self.band,
            'channel': self.channel,
            'hidden': self.hidden,
            'updated_at': self.updated_at.isoformat()
        }


class FirewallRule(db.Model):
    """Custom firewall rules"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    rule_type = db.Column(db.String(20))  # "port_forward", "custom", etc.
    source = db.Column(db.String(50))
    destination = db.Column(db.String(50))
    port = db.Column(db.Integer)
    protocol = db.Column(db.String(10))   # "tcp", "udp", "both"
    action = db.Column(db.String(10))     # "accept", "drop", "reject"
    enabled = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'rule_type': self.rule_type,
            'source': self.source,
            'destination': self.destination,
            'port': self.port,
            'protocol': self.protocol,
            'action': self.action,
            'enabled': self.enabled,
            'created_at': self.created_at.isoformat()
        }

class DeviceTraffic(db.Model):
    """Time-series traffic data for a device"""
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.Integer, db.ForeignKey('device.id'), nullable=False)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    
    # Bytes delta since last measurement
    bytes_sent = db.Column(db.BigInteger, default=0)    # Upload
    bytes_received = db.Column(db.BigInteger, default=0)# Download
    
    def to_dict(self):
        return {
            'timestamp': self.timestamp.isoformat(),
            'upload': self.bytes_sent,
            'download': self.bytes_received
        }

class SystemSettings(db.Model):
    """System-wide settings"""
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False, index=True)
    value = db.Column(db.Text)
    
    # New settings for NTFY and 2FA
    # We could store these as rows in the key-value table, but columns are cleaner for typed access
    # However, since the model is designed as K-V, let's stick to the K-V pattern for now
    # to avoid schema migration complexities if possible.
    # WAIT - The user prompt shows `SystemSettings` has `key` and `value`.
    # But usually settings are easier to manage if they are explicit columns or we have a helper.
    # Let's check how SystemSettings is used.
    
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'key': self.key,
            'value': self.value,
            'updated_at': self.updated_at.isoformat()
        }



class RouterConfig(db.Model):
    """Router mode configuration for WAN and LAN settings"""
    id = db.Column(db.Integer, primary_key=True)
    
    # WAN Settings (Internet Input)
    wan_mode = db.Column(db.String(10), default='dhcp')  # 'dhcp' or 'static'
    wan_static_ip = db.Column(db.String(15))
    wan_gateway = db.Column(db.String(15))
    wan_subnet_mask = db.Column(db.String(15), default='255.255.255.0')
    wan_dns_primary = db.Column(db.String(15), default='8.8.8.8')
    wan_dns_secondary = db.Column(db.String(15), default='8.8.4.4')
    
    # LAN Settings (Local Network)
    lan_ip = db.Column(db.String(15), default='192.168.10.1')
    lan_subnet_mask = db.Column(db.String(15), default='255.255.255.0')
    lan_dhcp_enabled = db.Column(db.Boolean, default=True)
    lan_dhcp_start = db.Column(db.String(15), default='192.168.10.100')
    lan_dhcp_end = db.Column(db.String(15), default='192.168.10.200')
    
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'wan': {
                'mode': self.wan_mode,
                'static_ip': self.wan_static_ip,
                'gateway': self.wan_gateway,
                'subnet_mask': self.wan_subnet_mask,
                'dns_primary': self.wan_dns_primary,
                'dns_secondary': self.wan_dns_secondary
            },
            'lan': {
                'ip': self.lan_ip,
                'subnet_mask': self.lan_subnet_mask,
                'dhcp_enabled': self.lan_dhcp_enabled,
                'dhcp_start': self.lan_dhcp_start,
                'dhcp_end': self.lan_dhcp_end
            },
            'updated_at': self.updated_at.isoformat()
        }


# Association table for Device <-> Service blocking
device_blocked_services = db.Table('device_blocked_services',
    db.Column('device_id', db.Integer, db.ForeignKey('device.id'), primary_key=True),
    db.Column('service_id', db.Integer, db.ForeignKey('service.id'), primary_key=True),
    db.Column('created_at', db.DateTime, default=datetime.utcnow)
)

class Service(db.Model):
    """Blocked service definition"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    label = db.Column(db.String(50))
    icon = db.Column(db.String(50))
    domain = db.Column(db.String(255)) # Main domain for this service
    enabled = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    ips = db.relationship('ServiceIP', backref='service', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'label': self.label,
            'icon': self.icon,
            'domain': self.domain,
            'enabled': self.enabled,
            'created_at': self.created_at.isoformat(),
            'ips': [ip.to_dict() for ip in self.ips],
            'ip_count': len(self.ips),
            'blocked_device_ids': [d.id for d in self.devices]
        }

class ServiceIP(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    service_id = db.Column(db.Integer, db.ForeignKey('service.id'), nullable=False)
    cidr = db.Column(db.String(50), nullable=False) # e.g. 157.240.0.0/16
    
    def to_dict(self):
        return {
            'id': self.id,
            'cidr': self.cidr
        }

class IPFilterRule(db.Model):
    """IP/Port filtering rules for whitelist/blacklist"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    ip_version = db.Column(db.Integer, default=4) # 4 or 6
    protocol = db.Column(db.String(10), default='all') # tcp, udp, icmp, all
    
    # Source
    source_ip = db.Column(db.String(50)) # IP or CIDR
    source_port = db.Column(db.String(20)) # Single port or range (e.g. 80, 80-90)
    
    # Destination
    dest_ip = db.Column(db.String(50))
    dest_port = db.Column(db.String(20))
    
    action = db.Column(db.String(10), default='drop') # 'accept' or 'drop'
    list_type = db.Column(db.String(10), default='blacklist') # 'whitelist' or 'blacklist'
    enabled = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'ip_version': self.ip_version,
            'protocol': self.protocol,
            'source_ip': self.source_ip,
            'source_port': self.source_port,
            'dest_ip': self.dest_ip,
            'dest_port': self.dest_port,
            'action': self.action,
            'list_type': self.list_type,
            'enabled': self.enabled,
            'created_at': self.created_at.isoformat()
        }


# Association table for Device <-> Domain Filter
device_domain_filters = db.Table('device_domain_filters',
    db.Column('device_id', db.Integer, db.ForeignKey('device.id'), primary_key=True),
    db.Column('filter_id', db.Integer, db.ForeignKey('domain_filter.id'), primary_key=True),
    db.Column('created_at', db.DateTime, default=datetime.utcnow)
)


class DomainFilterGroup(db.Model):
    """Groups of domain filters (like filter lists)"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)
    enabled = db.Column(db.Boolean, default=True)
    list_type = db.Column(db.String(20), default='blocklist')  # 'blocklist' or 'allowlist'
    source_url = db.Column(db.String(500))  # URL to fetch list from (e.g., adlist)
    color = db.Column(db.String(20), default='#64748b')  # Hex color code
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_updated = db.Column(db.DateTime)
    
    filters = db.relationship('DomainFilter', backref='group', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'enabled': self.enabled,
            'list_type': self.list_type,
            'source_url': self.source_url,
            'color': self.color,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'last_updated': self.last_updated.isoformat() if self.last_updated else None,
            'filter_count': len(self.filters)
        }


class DomainFilter(db.Model):
    """Individual domain filtering rules with regex support"""
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('domain_filter_group.id'), nullable=False)
    domain = db.Column(db.String(255), nullable=False, index=True)
    pattern_type = db.Column(db.String(20), default='exact')  # 'exact', 'wildcard', 'regex'
    regex_pattern = db.Column(db.String(500))  # For regex type filters
    enabled = db.Column(db.Boolean, default=True)
    blocking_enabled = db.Column(db.Boolean, default=True)  # Can be disabled per filter
    reason = db.Column(db.String(255))  # Why this domain is blocked
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    hit_count = db.Column(db.Integer, default=0)  # Number of times blocked
    last_hit = db.Column(db.DateTime)  # Last time this filter matched
    
    def to_dict(self):
        return {
            'id': self.id,
            'group_id': self.group_id,
            'domain': self.domain,
            'pattern_type': self.pattern_type,
            'regex_pattern': self.regex_pattern,
            'enabled': self.enabled,
            'blocking_enabled': self.blocking_enabled,
            'reason': self.reason,
            'created_at': self.created_at.isoformat(),
            'hit_count': self.hit_count,
            'last_hit': self.last_hit.isoformat() if self.last_hit else None
        }


class DNSQueryLog(db.Model):
    """Log of DNS queries processed"""
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    client_ip = db.Column(db.String(15), index=True)  # Device IP
    client_hostname = db.Column(db.String(255))
    query_domain = db.Column(db.String(255), nullable=False, index=True)
    query_type = db.Column(db.String(10))  # A, AAAA, MX, etc.
    response_code = db.Column(db.String(20))  # NOERROR, NXDOMAIN, REFUSED, etc.
    response_ip = db.Column(db.String(15))  # Resolved IP address
    was_blocked = db.Column(db.Boolean, default=False)
    blocked_by_filter_id = db.Column(db.Integer, db.ForeignKey('domain_filter.id'))
    upstream_server = db.Column(db.String(15))  # Which upstream DNS was used
    response_time_ms = db.Column(db.Integer)  # Response time in milliseconds
    device_id = db.Column(db.Integer, db.ForeignKey('device.id'))
    
    blocked_filter = db.relationship('DomainFilter', backref='query_logs')
    device = db.relationship('Device', backref='dns_logs')
    
    def to_dict(self):
        # Determine status display
        status = 'BLOCKED' if self.was_blocked else 'ALLOWED'
        
        # Get device group info if device is linked
        device_group = None
        if self.device and self.device.group:
            device_group = self.device.group
        
        # Get filter group info if blocked by filter
        filter_group = None
        if self.blocked_filter and self.blocked_filter.group:
            filter_group = {
                'id': self.blocked_filter.group.id,
                'name': self.blocked_filter.group.name
            }
        
        # Use filter group for blocked queries, device group for others
        matched_group = filter_group if filter_group else device_group
        
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat(),
            'domain': self.query_domain,  # Direct alias for UI
            'client_ip': self.client_ip,
            'client_hostname': self.client_hostname,
            'query_domain': self.query_domain,  # Keep for backwards compatibility
            'query_type': self.query_type,
            'response_code': self.response_code,
            'response_ip': self.response_ip,
            'status': status,  # Frontend-friendly status field
            'was_blocked': self.was_blocked,
            'blocked_by_filter_id': self.blocked_by_filter_id,
            'upstream_server': self.upstream_server,
            'response_time_ms': self.response_time_ms,
            'device_id': self.device_id,
            'response_type': self.query_type,  # Alias for frontend compatibility
            'group': device_group,  # Device group name
            'matched_group': matched_group  # Filter group or device group
        }


class DNSDomainStat(db.Model):
    """Statistics for DNS queries per domain"""
    id = db.Column(db.Integer, primary_key=True)
    domain = db.Column(db.String(255), unique=True, nullable=False, index=True)
    query_count = db.Column(db.Integer, default=0)
    blocked_count = db.Column(db.Integer, default=0)
    allowed_count = db.Column(db.Integer, default=0)
    last_queried = db.Column(db.DateTime, default=datetime.utcnow)
    first_queried = db.Column(db.DateTime, default=datetime.utcnow)
    category = db.Column(db.String(100))  # ads, malware, tracking, gaming, social, etc.
    
    def to_dict(self):
        return {
            'id': self.id,
            'domain': self.domain,
            'query_count': self.query_count,
            'blocked_count': self.blocked_count,
            'allowed_count': self.allowed_count,
            'last_queried': self.last_queried.isoformat() if self.last_queried else None,
            'first_queried': self.first_queried.isoformat() if self.first_queried else None,
            'category': self.category
        }


class DNSBlockList(db.Model):
    """DNS blocklist source (like adaway, pi-hole lists, etc.)"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)
    url = db.Column(db.String(500), nullable=False)
    enabled = db.Column(db.Boolean, default=True)
    category = db.Column(db.String(100))  # ads, malware, phishing, tracking, etc.
    domain_count = db.Column(db.Integer, default=0)
    last_updated = db.Column(db.DateTime)
    update_interval_hours = db.Column(db.Integer, default=24)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'url': self.url,
            'enabled': self.enabled,
            'category': self.category,
            'domain_count': self.domain_count,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None,
            'update_interval_hours': self.update_interval_hours,
            'created_at': self.created_at.isoformat()
        }
