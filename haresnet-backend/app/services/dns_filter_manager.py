import re
import subprocess
import os
from datetime import datetime
from flask import current_app
from app import db
from app.models import (
    DomainFilter, DNSQueryLog, DNSDomainStat, DomainFilterGroup,
    DNSBlockList, Device
)
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class LogFileHandler(FileSystemEventHandler):
    def __init__(self, log_file, callback):
        self.log_file = log_file
        self.callback = callback

    def on_modified(self, event):
        if event.src_path == self.log_file:
            with open(self.log_file, 'r') as f:
                lines = f.readlines()
                if lines:
                    self.callback(lines[-1])  # Process the last line

class DNSFilterManager:
    """Manages DNS filtering, blocking, and logging"""
    
    def __init__(self):
        # Use /app or /var/tmp if /etc/dnsmasq.d is not writable
        # Fallback paths for permission issues
        self.dnsmasq_conf_dir = '/etc/dnsmasq.d'
        self.blocklist_file = '/etc/dnsmasq.d/blocklist.conf'
        self.allowlist_file = '/etc/dnsmasq.d/allowlist.conf'
        self.addn_hosts_file = '/etc/dnsmasq.d/addn_hosts'
        
        # Check if /etc/dnsmasq.d is writable, otherwise use /app/config
        if not os.access('/etc/dnsmasq.d', os.W_OK):
            # Use application config directory instead
            self.dnsmasq_conf_dir = '/app/config/dnsmasq'
            self.blocklist_file = '/app/config/dnsmasq/blocklist.conf'
            self.allowlist_file = '/app/config/dnsmasq/allowlist.conf'
            self.addn_hosts_file = '/app/config/dnsmasq/addn_hosts'
        
        self.log_file = '/var/log/dnsmasq.log'
        
    def create_dnsmasq_filter_config(self):
        """Generate dnsmasq configuration for domain filtering"""
        try:
            # Build config referencing the actual paths being used
            addn_hosts_path = self.addn_hosts_file
            
            config_content = f"""# DNS Filtering Configuration
# Enable DNS query logging (sent to syslog)
log-queries=extra
log-facility=/var/log/dnsmasq.log

# Cache size
cache-size=10000

# Load blocklist configuration
# Blocklist entries will be auto-generated in blocklist.conf
conf-file={self.blocklist_file}

# Load allowlist configuration
conf-file={self.allowlist_file}

# Load additional hosts files for blocking
addn-hosts={addn_hosts_path}
"""
            # Create directory if it doesn't exist
            os.makedirs(self.dnsmasq_conf_dir, exist_ok=True)
            
            # Write main config file in the appropriate directory
            filter_conf = os.path.join(self.dnsmasq_conf_dir, 'dns-filter.conf')
            with open(filter_conf, 'w') as f:
                f.write(config_content)
            
            return True
        except Exception as e:
            import traceback
            current_app.logger.warning(f"Could not write dnsmasq filter config: {str(e)}")
            # Don't fail completely, just warn
            return False
    
    def apply_blocklist_to_dnsmasq(self):
        """Apply enabled blocklists to dnsmasq configuration"""
        try:
            # Get all enabled blocking filters
            blocklist_groups = DomainFilterGroup.query.filter(
                (DomainFilterGroup.enabled == True) &
                (DomainFilterGroup.list_type == 'blocklist')
            ).all()
            
            blocklist_ids = [g.id for g in blocklist_groups]
            
            filters = []
            if blocklist_ids:
                filters = DomainFilter.query.filter(
                    (DomainFilter.group_id.in_(blocklist_ids)) &
                    (DomainFilter.enabled == True) &
                    (DomainFilter.blocking_enabled == True)
                ).all()
            
            # Generate dnsmasq config lines
            # Format: server=/example.com/ (for blocking, returns NXDOMAIN or 0.0.0.0 if address=/#/)
            # address=/example.com/0.0.0.0 is the standard way to block
            
            lines = []
            for item in filters:
                domain = item.domain
                if item.pattern_type == 'wildcard':
                     # Convert *.example.com to example.com for dnsmasq (it handles subdomains auto)
                     if domain.startswith('*.'):
                         domain = domain[2:]
                     elif domain.startswith('.'):
                         domain = domain[1:]
                
                # Attempt to convert simple regex to dnsmasq wildcard
                # Regex: (^|\.)(facebook|fb)\.com$ -> facebook.com, fb.com
                if item.pattern_type == 'regex' and item.regex_pattern:
                    import re
                    # Look for standard pattern: (^|\.)(domains)\.tld$
                    # Try to match the structure manually or using regex
                    # Simple extraction: look for alphanumeric strings followed by \.tld
                    
                    # Heuristic: If it looks like (^|\.)example\.com$, convert to example.com
                    # If it has (a|b), split it.
                    
                    pattern = item.regex_pattern
                    
                    # Clean up the pattern for easier extraction
                    # Remove start/end anchors
                    clean_pattern = pattern.replace('^', '').replace('$', '')
                    # Replace escaped dots with real dots
                    clean_pattern = clean_pattern.replace(r'\.', '.')
                    
                    found_domains = set()
                    
                    # Strategy 1: Explicit domains in the pattern
                    # Handle alternations like (facebook|fb|messenger)
                    # Extract content inside parentheses
                    alternations = re.findall(r'\(([^)]+)\)', clean_pattern)
                    for group in alternations:
                        # Split by pipe
                        parts = group.split('|')
                        # Check what follows the group (e.g., .com)
                        # This is a bit advanced without full parsing, so we'll use a heuristic:
                        # If the regex ends with .com, append it to all parts.
                        suffix_match = re.search(r'\)\.([a-z]+)', clean_pattern)
                        suffix = "." + suffix_match.group(1) if suffix_match else ""
                        
                        for part in parts:
                            # Clean up partial regex chars
                            part = part.replace('\\', '').replace('.', '')
                            if part and suffix:
                                found_domains.add(f"{part}{suffix}")
                            elif part and '.' in part:
                                found_domains.add(part)

                    # Strategy 2: Grab full domains that look like domains
                    # valid-domain.tld where tld is 2+ chars
                    # Avoid capturing inside () if already handled, but finding all is safer as set handles dupes
                    matches = re.findall(r'[a-zA-Z0-9-]+\.[a-zA-Z]{2,}', clean_pattern)
                    for m in matches:
                        found_domains.add(m)
                        
                    # Add current filter domain as fallback if it looks valid
                    if '.' in item.domain and '*' not in item.domain and '(' not in item.domain:
                        found_domains.add(item.domain)
                        
                    for d in found_domains:
                        # skip if seems invalid regex artifact
                        if '|' in d or '(' in d or ')' in d or '\\' in d:
                            continue
                            
                        # Format as address=/domain/0.0.0.0
                        entry = f"address=/{d}/0.0.0.0"
                        if entry not in lines:
                            lines.append(entry)
                    
                    continue
                    
                lines.append(f"address=/{domain}/0.0.0.0")
            
            # Write to file
            with open(self.blocklist_file, 'w') as f:
                f.write('\n'.join(lines))
                
            current_app.logger.info(f"Updated dnsmasq blocklist with {len(lines)} entries")
            return True
            
        except Exception as e:
            current_app.logger.error(f"Error writing dnsmasq blocklist: {str(e)}")
            return False
    
    def apply_allowlist_to_dnsmasq(self):
        """Apply allowlist exceptions"""
        # Similar optimization as blocklist
        current_app.logger.info("Skipping dnsmasq allowlist write (using Python DNS Proxy)")
        return True
    
    def match_domain_against_filters(self, domain):
        """Check if a domain matches any active filter
        
        Returns:
            (bool, DomainFilter or None) - (is_blocked, filter_that_matched)
        """
        try:
            # Get all enabled blocking filters
            blocklist_groups = DomainFilterGroup.query.filter(
                (DomainFilterGroup.enabled == True) &
                (DomainFilterGroup.list_type == 'blocklist')
            ).all()
            
            blocklist_ids = [g.id for g in blocklist_groups]
            
            if not blocklist_ids:
                return False, None
            
            filters = DomainFilter.query.filter(
                (DomainFilter.group_id.in_(blocklist_ids)) &
                (DomainFilter.enabled == True) &
                (DomainFilter.blocking_enabled == True)
            ).all()
            
            # Check against allowlist first (allowlist has priority)
            allowlist_groups = DomainFilterGroup.query.filter(
                (DomainFilterGroup.enabled == True) &
                (DomainFilterGroup.list_type == 'allowlist')
            ).all()
            
            allowlist_ids = [g.id for g in allowlist_groups]
            allowlist_filters = []
            
            if allowlist_ids:
                allowlist_filters = DomainFilter.query.filter(
                    (DomainFilter.group_id.in_(allowlist_ids)) &
                    (DomainFilter.enabled == True)
                ).all()
            
            # Check against allowlist
            for filter_item in allowlist_filters:
                if self._domain_matches_filter(domain, filter_item):
                    return False, None  # Allowlisted, don't block
            
            # Check against blocklist
            for filter_item in filters:
                if self._domain_matches_filter(domain, filter_item):
                    return True, filter_item
            
            return False, None
        except Exception as e:
            current_app.logger.error(f"Error matching domain against filters: {str(e)}")
            return False, None
    
    def _domain_matches_filter(self, domain, filter_item):
        """Check if a domain matches a specific filter pattern"""
        try:
            if filter_item.pattern_type == 'exact':
                return domain.lower() == filter_item.domain.lower()
            
            elif filter_item.pattern_type == 'wildcard':
                # Convert *.example.com to regex
                filter_domain = filter_item.domain.lower()
                if filter_domain.startswith('*.'):
                    # Match domain and all subdomains
                    base_domain = filter_domain.replace('*.', '')
                    # Check for exact match of base domain
                    if domain.lower() == base_domain:
                        return True
                    
                    # Check for subdomains
                    pattern = base_domain.replace('.', r'\.')
                    pattern = f"^.*\\.{pattern}$"
                    return bool(re.match(pattern, domain.lower()))
                else:
                    # Wildcard at beginning
                    return domain.lower().endswith(filter_domain)
            
            elif filter_item.pattern_type == 'regex':
                if filter_item.regex_pattern:
                    try:
                        return bool(re.search(filter_item.regex_pattern, domain, re.IGNORECASE))
                    except re.error:
                        current_app.logger.error(f"Invalid regex pattern: {filter_item.regex_pattern}")
                        return False
            
            return False
        except Exception as e:
            current_app.logger.error(f"Error in domain matching: {str(e)}")
            return False
    
    def log_dns_query(self, **kwargs):
        """Log a single DNS query (now just a wrapper for batch)"""
        return self.log_dns_queries_batch([kwargs])

    def log_dns_queries_batch(self, queries_data):
        """Log a batch of DNS queries in a single transaction for performance and reduced locking"""
        if not queries_data:
            return True
            
        try:
            # Pre-fetch devices to avoid per-query lookups
            ips = [q.get('client_ip') for q in queries_data if q.get('client_ip')]
            devices = {d.ip: d for d in Device.query.filter(Device.ip.in_(ips)).all()} if ips else {}
            
            # Pre-fetch existing domain stats to avoid per-query lookups
            domains = [q.get('query_domain') for q in queries_data if q.get('query_domain')]
            existing_stats = {s.domain: s for s in DNSDomainStat.query.filter(DNSDomainStat.domain.in_(domains)).all()} if domains else {}
            
            for q_data in queries_data:
                client_ip = q_data.get('client_ip')
                query_domain = q_data.get('query_domain')
                was_blocked = q_data.get('was_blocked', False)
                blocked_by_filter_id = q_data.get('blocked_by_filter_id')
                device_id = q_data.get('device_id')
                
                # Resolve device and hostname
                device = devices.get(client_ip)
                if not device_id and device:
                    device_id = device.id
                client_hostname = device.hostname if device else None
                
                query_log = DNSQueryLog(
                    timestamp=q_data.get('timestamp') or datetime.utcnow(),
                    client_ip=client_ip,
                    client_hostname=client_hostname,
                    query_domain=query_domain,
                    query_type=q_data.get('query_type', 'A'),
                    response_code=q_data.get('response_code', 'NOERROR'),
                    response_ip=q_data.get('response_ip'),
                    was_blocked=was_blocked,
                    blocked_by_filter_id=blocked_by_filter_id,
                    upstream_server=q_data.get('upstream_server'),
                    response_time_ms=q_data.get('response_time_ms', 0),
                    device_id=device_id
                )
                db.session.add(query_log)
                
                # Update statistics (in memory first)
                if query_domain:
                    stat = existing_stats.get(query_domain)
                    if not stat:
                        stat = DNSDomainStat(domain=query_domain)
                        db.session.add(stat)
                        existing_stats[query_domain] = stat
                    
                    stat.query_count += 1
                    if was_blocked:
                        stat.blocked_count += 1
                    else:
                        stat.allowed_count += 1
                    stat.last_queried = datetime.utcnow()
                
                # Update filter hit count
                if blocked_by_filter_id:
                    filter_item = DomainFilter.query.get(blocked_by_filter_id)
                    if filter_item:
                        filter_item.hit_count += 1
                        filter_item.last_hit = datetime.utcnow()

            db.session.commit()
            return True
        except Exception as e:
            current_app.logger.error(f"Error in DNS batch logging: {str(e)}")
            db.session.rollback()
            return False
        finally:
            db.session.remove()
    
    def _update_domain_stats(self, domain, was_blocked=False, blocked_by_filter_id=None):
        """Update domain statistics"""
        try:
            # Find or create stat entry
            stat = DNSDomainStat.query.filter_by(domain=domain).first()
            
            if not stat:
                stat = DNSDomainStat(domain=domain)
                db.session.add(stat)
            
            stat.query_count += 1
            if was_blocked:
                stat.blocked_count += 1
            else:
                stat.allowed_count += 1
            stat.last_queried = datetime.utcnow()
            
            # Try to categorize the domain
            if blocked_by_filter_id:
                filter_item = DomainFilter.query.get(blocked_by_filter_id)
                if filter_item and filter_item.group:
                    if 'ads' in filter_item.group.name.lower():
                        stat.category = 'ads'
                    elif 'malware' in filter_item.group.name.lower():
                        stat.category = 'malware'
                    elif 'track' in filter_item.group.name.lower():
                        stat.category = 'tracking'
        except Exception as e:
            current_app.logger.error(f"Error updating domain stats: {str(e)}")
    
    def restart_dnsmasq(self):
        """Restart dnsmasq service to apply filter changes (works in Docker)"""
        try:
            # Try systemctl first
            result = subprocess.run(
                ['systemctl', 'restart', 'dnsmasq'],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                current_app.logger.info("Dnsmasq restarted via systemctl")
                return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        except Exception:
            pass
        
        # Fallback: pkill + relaunch (Docker container)
        try:
            current_app.logger.info("Restarting dnsmasq via pkill + relaunch...")
            subprocess.run(['pkill', '-x', 'dnsmasq'], capture_output=True, timeout=3)
            import time
            time.sleep(0.5)
            result = subprocess.run(
                ['dnsmasq', '--conf-file=/etc/dnsmasq.conf'],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                current_app.logger.info("Dnsmasq restarted successfully via pkill + relaunch")
                return True
            else:
                current_app.logger.warning(f"dnsmasq relaunch failed: {result.stderr}")
                return False
        except Exception as e:
            current_app.logger.error(f"Failed to restart dnsmasq: {str(e)}")
            return False
    
    def get_filter_stats(self):
        """Get overall filter statistics"""
        try:
            stats = {
                'total_blocked_today': DNSQueryLog.query.filter(
                    (DNSQueryLog.was_blocked == True) &
                    (DNSQueryLog.timestamp >= datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0))
                ).count(),
                'total_queries_today': DNSQueryLog.query.filter(
                    DNSQueryLog.timestamp >= datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
                ).count(),
                'total_active_filters': DomainFilter.query.filter(
                    (DomainFilter.enabled == True) &
                    (DomainFilter.blocking_enabled == True)
                ).count(),
                'total_blocklists': DomainFilterGroup.query.filter(
                    (DomainFilterGroup.enabled == True) &
                    (DomainFilterGroup.list_type == 'blocklist')
                ).count(),
                'top_blocked_domains': self._get_top_blocked_domains(10),
                'top_clients': self._get_top_clients(10)
            }
            return stats
        except Exception as e:
            current_app.logger.error(f"Error getting filter stats: {str(e)}")
            return {}
    
    def _get_top_blocked_domains(self, limit=10):
        """Get top blocked domains"""
        try:
            from sqlalchemy import func
            results = db.session.query(
                DNSDomainStat.domain,
                DNSDomainStat.blocked_count
            ).filter(
                DNSDomainStat.blocked_count > 0
            ).order_by(
                DNSDomainStat.blocked_count.desc()
            ).limit(limit).all()
            
            return [{'domain': r[0], 'blocked_count': r[1]} for r in results]
        except Exception as e:
            current_app.logger.error(f"Error getting top blocked domains: {str(e)}")
            return []
    
    def _get_top_clients(self, limit=10):
        """Get top clients making queries"""
        try:
            from sqlalchemy import func
            results = db.session.query(
                DNSQueryLog.client_ip,
                func.count(DNSQueryLog.id).label('query_count')
            ).filter(
                DNSQueryLog.client_ip.isnot(None)
            ).group_by(
                DNSQueryLog.client_ip
            ).order_by(
                func.count(DNSQueryLog.id).desc()
            ).limit(limit).all()
            
            return [{'client_ip': r[0], 'query_count': r[1]} for r in results]
        except Exception as e:
            current_app.logger.error(f"Error getting top clients: {str(e)}")
            return []
    
    def cleanup_old_logs(self, days=30):
        """Clean up DNS query logs older than specified days"""
        try:
            from datetime import timedelta
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            deleted_count = DNSQueryLog.query.filter(
                DNSQueryLog.timestamp < cutoff_date
            ).delete()
            db.session.commit()
            current_app.logger.info(f"Cleaned up {deleted_count} old DNS logs")
            return deleted_count
        except Exception as e:
            current_app.logger.error(f"Error cleaning up DNS logs: {str(e)}")
            db.session.rollback()
            return 0
    
    def start_log_monitoring(self):
        """Start monitoring the dnsmasq log file for real-time updates."""
        if not HAS_WATCHDOG:
            current_app.logger.warning("watchdog module not available, log monitoring disabled")
            return
        
        if not os.path.exists(self.log_file):
            current_app.logger.error(f"Log file {self.log_file} does not exist.")
            return

        def process_log_line(line):
            # Parse the log line and update the database
            current_app.logger.info(f"Processing log line: {line.strip()}")
            # Add log parsing logic here

        event_handler = LogFileHandler(self.log_file, process_log_line)
        observer = Observer()
        observer.schedule(event_handler, path=os.path.dirname(self.log_file), recursive=False)
        observer_thread = threading.Thread(target=observer.start, daemon=True)
        observer_thread.start()
        current_app.logger.info("Started monitoring dnsmasq log file for real-time updates.")
