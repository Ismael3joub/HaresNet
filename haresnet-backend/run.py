#!/usr/bin/env python3
import eventlet
eventlet.monkey_patch()
import os
from app import create_app, db, socketio
from app.services.device_discovery import DeviceDiscovery
from app.services.scheduler import SchedulerService
from apscheduler.schedulers.background import BackgroundScheduler

# Create app instance
app = create_app(os.getenv('FLASK_ENV', 'default'))

from app.services.system_monitor import monitor as system_monitor


# Initialize services
device_discovery = DeviceDiscovery()

# Initialize traffic monitor
from app.services.traffic_monitor import TrafficMonitor
traffic_monitor = TrafficMonitor()

# Initialize firewall
from app.services.nftables_manager import NftablesManager
with app.app_context():
    nft_manager = NftablesManager()
    if app.config.get('INITIALIZE_FIREWALL', True):
        try:
            nft_manager.initialize_firewall()
            print("Firewall initialized", flush=True)
        except Exception as e:
            print(f"Failed to initialize firewall: {e}", flush=True)
    else:
        print("Skipping firewall initialization (disabled by config)", flush=True)

discovery_scheduler = BackgroundScheduler()

def discovery_job():
    # Poll for devices
    with app.app_context():
        device_discovery.update_device_database()
        
        # Broadcast system stats
        stats = system_monitor.get_stats()
        print(f"DEBUG: Emitting stats: {stats}", flush=True)
        socketio.emit('system_stats', stats)

def traffic_monitoring_job():
    """Collect traffic statistics for all devices"""
    with app.app_context():
        traffic_monitor.collect_traffic_stats()
        
        # Optionally emit current traffic rates via Socket.IO
        try:
            rates = traffic_monitor.get_current_rates()
            if rates:
                socketio.emit('traffic_rates', rates)
        except Exception as e:
            print(f"Error emitting traffic rates: {e}", flush=True)


if app.config.get('ENABLE_DISCOVERY', True):
    discovery_interval = app.config.get('DISCOVERY_INTERVAL_SECONDS', 2)
    discovery_scheduler.add_job(
        func=discovery_job,
        trigger='interval',
        seconds=discovery_interval,
        id='device_discovery'
    )
    discovery_scheduler.start()
else:
    print('Device discovery disabled by config', flush=True)

# Add traffic monitoring job
if app.config.get('ENABLE_TRAFFIC_MONITORING', True):
    traffic_interval = app.config.get('TRAFFIC_MONITORING_INTERVAL_SECONDS', 10)
    discovery_scheduler.add_job(
        func=traffic_monitoring_job,
        trigger='interval',
        seconds=traffic_interval,
        id='traffic_monitoring'
    )
    print(f'Traffic monitoring enabled (interval: {traffic_interval}s)', flush=True)
else:
    print('Traffic monitoring disabled by config', flush=True)


# Initialize schedule enforcement
if app.config.get('ENABLE_SCHEDULER', True):
    print('Starting schedule enforcement service...', flush=True)
    schedule_service = SchedulerService(app)
    schedule_service.start()
    print('Schedule enforcement service started successfully', flush=True)
else:
    print('Scheduler disabled by config', flush=True)

# Initialize DNS Filter Manager
print('Initializing DNS filtering system...', flush=True)
from app.services.dns_filter_manager import DNSFilterManager
from app.services.blocklist_manager import BlocklistManager
from app.services.dns_log_parser import DNSLogParser

dns_filter_manager = DNSFilterManager()
blocklist_manager = BlocklistManager()
dns_log_parser = DNSLogParser()

with app.app_context():
    try:
        # Ensure dnsmasq filter files exist (prevent startup crash)
        import os
        os.makedirs('/etc/dnsmasq.d', exist_ok=True)
        for f in ['/etc/dnsmasq.d/blocklist.conf', '/etc/dnsmasq.d/allowlist.conf']:
            if not os.path.exists(f):
                open(f, 'w').close()
        
        # Create DNS filter configuration
        dns_filter_manager.create_dnsmasq_filter_config()
        
        # Add default blocklists if none exist
        from app.models import DNSBlockList
        if DNSBlockList.query.count() == 0:
            print('Adding default blocklists...', flush=True)
            blocklist_manager.add_default_blocklists()
        
        # Apply filter rules (writes blocklist.conf and allowlist.conf)
        dns_filter_manager.apply_blocklist_to_dnsmasq()
        dns_filter_manager.apply_allowlist_to_dnsmasq()
        
        # Restart dnsmasq to pick up filter files
        dns_filter_manager.restart_dnsmasq()
        
        # Enable dnsmasq logging
        dns_log_parser.enable_logging_in_dnsmasq()
        
        # Apply service blocking rules (nftables) to enforce from first query
        print('Applying service blocking rules...', flush=True)
        nft_manager.apply_service_blocking_rules()
        
        print('DNS filtering system initialized successfully', flush=True)
    except Exception as e:
        print(f'Warning: DNS filtering system initialization failed: {e}', flush=True)
        import traceback
        traceback.print_exc()

# Add DNS log parsing job (every 30 seconds)
# def dns_log_parsing_job():
#     """Parse dnsmasq logs and update DNS statistics"""
#     with app.app_context():
#         try:
#             processed = dns_log_parser.parse_dnsmasq_logs()
#             if processed > 0:
#                 print(f'Processed {processed} DNS log entries', flush=True)
#         except Exception as e:
#             print(f'Error parsing DNS logs: {e}', flush=True)

# Start DNS Proxy Service
print('Starting DNS Proxy Service...', flush=True)
from app.services.dns_proxy import DNSProxyService
dns_proxy = DNSProxyService()
dns_proxy.start()

# Add blocklist update job (every 24 hours)
def blocklist_update_job():
    """Update all enabled blocklists"""
    with app.app_context():
        try:
            print('Starting blocklist update...', flush=True)
            results = blocklist_manager.update_all_blocklists()
            
            if results:
                # Reapply rules after update
                dns_filter_manager.apply_blocklist_to_dnsmasq()
                dns_filter_manager.restart_dnsmasq()
                print(f'Blocklist update completed', flush=True)
        except Exception as e:
            print(f'Error updating blocklists: {e}', flush=True)

# Add DNS log cleanup job (every 7 days)
def dns_log_cleanup_job():
    """Clean up old DNS logs"""
    with app.app_context():
        try:
            deleted = dns_filter_manager.cleanup_old_logs(days=30)
            print(f'Cleaned up {deleted} old DNS log entries', flush=True)
        except Exception as e:
            print(f'Error cleaning up DNS logs: {e}', flush=True)

# Schedule DNS monitoring jobs
if app.config.get('ENABLE_DNS_FILTER', True):
    # discovery_scheduler.add_job(
    #     func=dns_log_parsing_job,
    #     trigger='interval',
    #     seconds=2,
    #     id='dns_log_parsing'
    # )
    
    discovery_scheduler.add_job(
        func=blocklist_update_job,
        trigger='interval',
        hours=24,
        id='blocklist_update'
    )
    
    discovery_scheduler.add_job(
        func=dns_log_cleanup_job,
        trigger='interval',
        days=1,
        id='dns_log_cleanup'
    )
    
    print('DNS filtering jobs scheduled successfully', flush=True)
else:
    print('DNS filtering disabled by config', flush=True)

import signal
import sys
import subprocess

def signal_handler(sig, frame):
    """Handle termination signals to clean up background processes"""
    print("\nShutting down HaresNet Router...")
    
    # Kill hostapd
    print("Stopping hostapd...")
    subprocess.run(['pkill', 'hostapd'], check=False)
    
    # Kill dnsmasq
    print("Stopping dnsmasq...")
    subprocess.run(['pkill', 'dnsmasq'], check=False)
    
    print("Cleanup complete. Exiting.")
    sys.exit(0)

if __name__ == '__main__':
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Run Flask app with SocketIO
    socketio.run(
        app,
        host='0.0.0.0',
        port=int(os.getenv('PORT', 80)),
        debug=os.getenv('FLASK_ENV') == 'development',
        allow_unsafe_werkzeug=True
    )
