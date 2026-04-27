#!/usr/bin/env python3
"""
DNS Log Parser Service
Start the background service to continuously parse real DNS logs from dnsmasq
"""
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
from app.services.dns_log_parser import DNSLogParser
import time
import signal

app = create_app()
log_parser = None

def signal_handler(sig, frame):
    """Handle shutdown signal"""
    print('\n\n⏹️  Stopping DNS log parser...')
    if log_parser:
        print('✓ Log parser stopped')
    sys.exit(0)

def main():
    global log_parser
    
    print("\n" + "="*60)
    print("DNS Log Parser Service")
    print("="*60)
    print("Reading real DNS queries from dnsmasq log file...")
    print("Press Ctrl+C to stop\n")
    
    signal.signal(signal.SIGINT, signal_handler)
    
    with app.app_context():
        log_parser = DNSLogParser()
        
        # Enable logging first
        print("🔧 Enabling dnsmasq DNS logging...")
        log_parser.enable_logging_in_dnsmasq()
        print("✓ Logging enabled\n")
        
        # Start parsing
        print("📊 Starting DNS log monitoring...")
        print(f"   Log file: {log_parser.log_file}\n")
        
        iteration = 0
        while True:
            iteration += 1
            try:
                # Parse logs every 5 seconds
                new_logs = log_parser.parse_dnsmasq_logs()
                
                if new_logs > 0:
                    print(f"[{iteration}] Found {new_logs} new DNS queries")
                    
                    # Show recent logs
                    from app.models import DNSQueryLog
                    recent = DNSQueryLog.query.order_by(
                        DNSQueryLog.timestamp.desc()
                    ).limit(3).all()
                    
                    if recent:
                        for log in recent:
                            status = "🔴 BLOCK" if log.was_blocked else "🟢 ALLOW"
                            print(f"     {status} | {log.query_domain} | {log.client_ip}")
                
                time.sleep(5)  # Check every 5 seconds
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"⚠️  Error: {str(e)}")
                time.sleep(5)

if __name__ == '__main__':
    main()
