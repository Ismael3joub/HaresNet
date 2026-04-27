import os
from datetime import timedelta

class Config:
    """Base configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///haresnet.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Enable WAL mode for SQLite to allow concurrent reads/writes
    # This prevents "database is locked" errors from concurrent background jobs
    SQLALCHEMY_ENGINE_OPTIONS = {
        'connect_args': {'timeout': 15},
        'pool_pre_ping': True,
    }
    
    # JWT Configuration
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'jwt-secret-key-change-in-production'
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
    
    # Network Configuration
    WAN_INTERFACE = os.environ.get('WAN_INTERFACE', 'eth0')
    LAN_INTERFACE = os.environ.get('LAN_INTERFACE', 'wlan0')
    LAN_IP = os.environ.get('LAN_IP', '192.168.10.1')
    LAN_NETMASK = os.environ.get('LAN_NETMASK', '255.255.255.0')
    DHCP_RANGE_START = os.environ.get('DHCP_RANGE_START', '192.168.10.100')
    DHCP_RANGE_END = os.environ.get('DHCP_RANGE_END', '192.168.10.200')
    
    # Service Paths
    HOSTAPD_CONF = '/etc/hostapd/hostapd.conf'
    DNSMASQ_CONF = '/etc/dnsmasq.conf'
    DNSMASQ_LEASES = '/var/lib/misc/dnsmasq.leases'
    
    # Default Admin Credentials (change on first login)
    DEFAULT_ADMIN_USER = 'admin'
    DEFAULT_ADMIN_PASSWORD = 'haresnet2024'
    # Feature flags and intervals (use environment variables to override for tests)
    ENABLE_SCHEDULER = os.environ.get('ENABLE_SCHEDULER', '1') == '1'
    SCHEDULE_INTERVAL_MINUTES = int(os.environ.get('SCHEDULE_INTERVAL_MINUTES', '1'))
    ENABLE_DISCOVERY = os.environ.get('ENABLE_DISCOVERY', '1') == '1'
    DISCOVERY_INTERVAL_SECONDS = int(os.environ.get('DISCOVERY_INTERVAL_SECONDS', '2'))
    INITIALIZE_FIREWALL = os.environ.get('INITIALIZE_FIREWALL', '1') == '1'
    
    # DNS Filtering Configuration
    ENABLE_DNS_FILTER = os.environ.get('ENABLE_DNS_FILTER', '1') == '1'
    DNS_LOG_RETENTION_DAYS = int(os.environ.get('DNS_LOG_RETENTION_DAYS', '30'))
    DNS_LOG_PARSE_INTERVAL_SECONDS = int(os.environ.get('DNS_LOG_PARSE_INTERVAL_SECONDS', '30'))
    BLOCKLIST_UPDATE_INTERVAL_HOURS = int(os.environ.get('BLOCKLIST_UPDATE_INTERVAL_HOURS', '24'))
    
    # Blynk Configuration
    BLYNK_TEMPLATE_ID = os.environ.get('BLYNK_TEMPLATE_ID')
    BLYNK_TEMPLATE_NAME = os.environ.get('BLYNK_TEMPLATE_NAME')
    BLYNK_AUTH_TOKEN = os.environ.get('BLYNK_AUTH_TOKEN')
    BLYNK_ENABLED = os.environ.get('BLYNK_ENABLED', '0') == '1'
    TRAFFIC_THRESHOLD_MBPS = float(os.environ.get('TRAFFIC_THRESHOLD_MBPS', '10.0'))

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:////tmp/test.db'
    WTF_CSRF_ENABLED = False

config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
