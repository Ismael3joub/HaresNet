#!/usr/bin/env python3
"""
Enable DNS Query Logging
Configure dnsmasq to log DNS queries and start the log parser
"""
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app, db
from app.services.dns_log_parser import DNSLogParser
from app.services.dns_filter_manager import DNSFilterManager
import subprocess

app = create_app()

def enable_dns_logging():
    """Enable DNS logging in dnsmasq"""
    print("🔧 Enabling DNS Query Logging in dnsmasq...")
    
    # Read current dnsmasq config
    config_file = '/etc/dnsmasq.conf'
    
    try:
        with open(config_file, 'r') as f:
            lines = f.readlines()
        
        # Check if log-queries is already enabled
        has_log_queries = any('log-queries' in line and not line.strip().startswith('#') for line in lines)
        has_log_facility = any('log-facility' in line and not line.strip().startswith('#') for line in lines)
        
        if has_log_queries and has_log_facility:
            print("✓ DNS logging already enabled")
            return True
        
        # If not enabled, enable it
        if not has_log_queries or not has_log_facility:
            # Find the logging section and uncomment it
            new_lines = []
            for i, line in enumerate(lines):
                if line.strip() == '# log-queries':
                    new_lines.append('log-queries\n')
                    # Also add log-facility if not present
                    if not has_log_facility:
                        new_lines.append('log-facility=/var/log/dnsmasq.log\n')
                    # Skip the original commented line
                else:
                    new_lines.append(line)
            
            with open(config_file, 'w') as f:
                f.writelines(new_lines)
            
            print("✓ Updated dnsmasq.conf to enable logging")
            
            # Restart dnsmasq
            print("🔄 Restarting dnsmasq...")
            result = subprocess.run(['sudo', 'systemctl', 'restart', 'dnsmasq'], 
                                  capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✓ dnsmasq restarted successfully")
                return True
            else:
                print(f"✗ Failed to restart dnsmasq: {result.stderr}")
                return False
    
    except PermissionError:
        print("⚠️  Need sudo privileges to modify dnsmasq.conf")
        print("   Run with: sudo python3 enable_dns_logging.py")
        return False
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return False

def enable_log_parsing():
    """Enable DNS log parsing"""
    print("\n📊 Configuring DNS Log Parser...")
    
    with app.app_context():
        try:
            log_parser = DNSLogParser()
            log_parser.enable_logging_in_dnsmasq()
            print("✓ DNS Log Parser enabled")
            return True
        except Exception as e:
            print(f"⚠️  Log parser error: {str(e)}")
            return True  # Don't fail, logging might be manually configured

def test_real_queries():
    """Test by making real DNS queries"""
    print("\n🔍 Testing DNS Query Logging...")
    print("   Making test DNS queries...")
    
    test_domains = [
        'google.com',
        'github.com',
        'stackoverflow.com',
    ]
    
    for domain in test_domains:
        try:
            # Use nslookup to make a real DNS query
            result = subprocess.run(['nslookup', domain], capture_output=True, timeout=3)
            print(f"   ✓ Queried: {domain}")
        except Exception as e:
            print(f"   ⚠️  Could not query {domain}: {str(e)}")
    
    print("\n💡 Real queries should now appear in the database!")
    print("   Check with: python3 check_dns_logs.py --logs")

def main():
    print("\n" + "="*60)
    print("DNS Query Logging Setup")
    print("="*60)
    
    # Try to enable logging (might need sudo)
    if enable_dns_logging():
        enable_log_parsing()
        
        print("\n" + "="*60)
        print("✓ Setup Complete!")
        print("="*60)
        print("\nNext Steps:")
        print("1. Make real DNS queries from your devices")
        print("2. Check logs with: python3 check_dns_logs.py --logs")
        print("3. View stats with: python3 check_dns_logs.py --stats")
        print("4. Check real-time logs in the frontend DNS Filter page")
    else:
        print("\n" + "="*60)
        print("⚠️  Setup Requires Root Privileges")
        print("="*60)
        print("\nTo enable DNS logging, run:")
        print("  sudo python3 enable_dns_logging.py")

if __name__ == '__main__':
    main()
