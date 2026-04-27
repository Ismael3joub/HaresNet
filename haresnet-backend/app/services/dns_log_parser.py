import os
import re
import subprocess
from datetime import datetime
from flask import current_app
from app import db
from app.models import DNSQueryLog, Device
from app.services.dns_filter_manager import DNSFilterManager
import threading
import time

class DNSLogParser:
    """Parses dnsmasq logs and populates DNS query database"""
    
    def __init__(self):
        self.log_file = '/var/log/dnsmasq.log'
        self.last_position = 0
        self.dns_manager = DNSFilterManager()
        self.patterns = {
            # Format 1: query[A] domain.com from 192.168.1.100
            'query_standard': re.compile(r'query\[([A-Z0-9]+)\]\s+(\S+)\s+from\s+([0-9.]+)'),
            # Format 2: dnsmasq[123]: query[A] domain.com from 192.168.1.100
            'query_with_pid': re.compile(r'dnsmasq\[\d+\]:\s+query\[([A-Z0-9]+)\]\s+(\S+)\s+from\s+([0-9.]+)'),
            # Format 3: ... query[A] domain.com from 192.168.1.100 (generic fallback)
            'query_generic': re.compile(r'query\[([A-Z0-9]+)\]\s+(\S+)\s+from\s+([0-9.]+)'),
            
            # Reply formats
            'reply': re.compile(r'reply\s+(\S+)\s+is\s+([\d.]+|<CNAME>|NXDOMAIN|NODATA)'),
            'cached': re.compile(r'cached\s+(\S+)\s+is\s+([\d.]+|<CNAME>|NXDOMAIN|NODATA)'),
            
            # Timestamp: "Feb 14 18:19:37" at the start of each log line
            'timestamp': re.compile(r'^([A-Z][a-z]{2})\s+(\d{1,2})\s+(\d{2}:\d{2}:\d{2})'),
        }
    
    def parse_dnsmasq_logs(self):
        """Parse dnsmasq logs and update database"""
        try:
            if not os.path.exists(self.log_file):
                # Try creating it if it doesn't exist to avoid errors
                # open(self.log_file, 'a').close()
                current_app.logger.warning(f"Dnsmasq log file not found: {self.log_file}")
                return 0
            
            # Read new lines from log file
            with open(self.log_file, 'r', errors='ignore') as f:
                # Seek to last known position
                f.seek(self.last_position)
                lines = f.readlines()
                self.last_position = f.tell()
            
            processed_count = 0
            
            queries_to_log = []
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Parse query line
                query_match = self._parse_query_line(line)
                if query_match:
                    domain = query_match['domain']
                    client_ip = query_match['client_ip']
                    query_type = query_match['query_type']
                    log_timestamp = query_match.get('timestamp')
                    
                    # Check if domain should be blocked
                    is_blocked, matched_filter = self.dns_manager.match_domain_against_filters(domain)
                    
                    # Add to batch
                    queries_to_log.append({
                        'client_ip': client_ip,
                        'query_domain': domain,
                        'query_type': query_type,
                        'was_blocked': is_blocked,
                        'blocked_by_filter_id': matched_filter.id if matched_filter else None,
                        'response_code': 'NOERROR' if not is_blocked else 'NXDOMAIN',
                        'response_ip': '127.0.0.1' if is_blocked else None,
                        'response_time_ms': 0,
                        'timestamp': log_timestamp
                    })
                    processed_count += 1
            
            # Process batch
            if queries_to_log:
                self.dns_manager.log_dns_queries_batch(queries_to_log)
            
            if processed_count > 0:
                try:
                    # Emit updated stats via WebSocket
                    from app import socketio
                    stats = self.dns_manager.get_filter_stats()
                    socketio.emit('dns_stats_update', stats)
                except Exception as e:
                    current_app.logger.error(f"Error emitting stats update: {e}")
            
            return processed_count
        except Exception as e:
            current_app.logger.error(f"Error parsing dnsmasq logs: {str(e)}")
            return 0
    
    def _extract_timestamp(self, line):
        """Extract real timestamp from a dnsmasq log line.
        Format: 'Feb 14 18:19:37 ...' 
        Returns a datetime object or None."""
        try:
            ts_match = self.patterns['timestamp'].match(line)
            if ts_match:
                month_str = ts_match.group(1)
                day = int(ts_match.group(2))
                time_str = ts_match.group(3)
                year = datetime.now().year
                ts_string = f"{month_str} {day} {year} {time_str}"
                return datetime.strptime(ts_string, "%b %d %Y %H:%M:%S")
        except Exception:
            pass
        return None
    
    def _parse_query_line(self, line):
        """Parse a query line from dnsmasq log"""
        try:
            # Skip non-query lines early
            if 'query[' not in line:
                return None

            # Extract real timestamp from the log line
            log_timestamp = self._extract_timestamp(line)

            # Try patterns in order of specificity
            
            # 1. PID format (most common in syslog)
            match = self.patterns['query_with_pid'].search(line)
            if match:
                return {
                    'query_type': match.group(1),
                    'domain': match.group(2),
                    'client_ip': match.group(3),
                    'timestamp': log_timestamp,
                }
            
            # 2. Standard format (direct logging)
            match = self.patterns['query_standard'].search(line)
            if match:
                return {
                    'query_type': match.group(1),
                    'domain': match.group(2),
                    'client_ip': match.group(3),
                    'timestamp': log_timestamp,
                }

            # 3. Generic fallback
            match = self.patterns['query_generic'].search(line)
            if match:
                return {
                    'query_type': match.group(1),
                    'domain': match.group(2),
                    'client_ip': match.group(3),
                    'timestamp': log_timestamp,
                }

        except Exception as e:
            current_app.logger.debug(f"Error parsing query line '{line}': {e}")
        return None
    
    def _parse_reply_line(self, line):
        """Parse a reply line from dnsmasq log"""
        try:
            match = self.patterns['reply'].search(line)
            if match:
                return {
                    'domain': match.group(1),
                    'response_ip': match.group(2)
                }
        except Exception as e:
            current_app.logger.debug(f"Error parsing reply line: {e}")
        return None
    
    def _is_simple_query_line(self, line):
        """Check if line contains a DNS query"""
        return 'queries from' in line or 'query' in line.lower()
    
    def _log_dns_query_from_line(self, line):
        """Extract and log a DNS query from a dnsmasq log line"""
        try:
            # Try to extract domain and client IP
            # Dnsmasq log format varies, but typically includes:
            # "192.168.1.100 google.com (A)"
            
            ip_pattern = r'(\d+\.\d+\.\d+\.\d+)'
            domain_pattern = r'(\S+)\s+\(([A-Z]+)\)'
            
            ip_match = re.search(ip_pattern, line)
            domain_match = re.search(domain_pattern, line)
            
            if ip_match and domain_match:
                client_ip = ip_match.group(1)
                domain = domain_match.group(1)
                query_type = domain_match.group(2)
                
                # Check if domain should be blocked
                is_blocked, matched_filter = self.dns_manager.match_domain_against_filters(domain)
                
                # Log the query
                self.dns_manager.log_dns_query(
                    client_ip=client_ip,
                    query_domain=domain,
                    query_type=query_type,
                    was_blocked=is_blocked,
                    blocked_by_filter_id=matched_filter.id if matched_filter else None,
                    response_time_ms=0  # Not available from standard dnsmasq logs
                )
        except Exception as e:
            current_app.logger.debug(f"Error logging DNS query from line: {e}")
    
    def enable_logging_in_dnsmasq(self):
        """Enable DNS query logging in dnsmasq if not already enabled"""
        try:
            dnsmasq_conf = '/etc/dnsmasq.conf'
            
            # Check if logging is already enabled
            if os.path.exists(dnsmasq_conf):
                with open(dnsmasq_conf, 'r') as f:
                    content = f.read()
                    if 'log-queries' in content:
                        current_app.logger.info("Dnsmasq logging already enabled")
                        return True
            
            # Enable logging
            logging_config = """
# DNS Query Logging for HaresNet Filter
log-queries=extra
log-facility=/var/log/dnsmasq.log
"""
            
            with open(dnsmasq_conf, 'a') as f:
                f.write(logging_config)
            
            # Reload dnsmasq
            try:
                result = subprocess.run(
                    ['systemctl', 'reload', 'dnsmasq'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    current_app.logger.info("Dnsmasq logging enabled and reloaded successfully")
                    return True
                else:
                    # Try service command
                    subprocess.run(['service', 'dnsmasq', 'reload'], capture_output=True, timeout=5)
                    current_app.logger.info("Dnsmasq logging enabled (reload via service)")
                    return True
            except FileNotFoundError:
                # systemctl not available, but config was written
                current_app.logger.warning("Logging config saved but systemctl not available - dnsmasq may need manual reload")
                return True
            except subprocess.TimeoutExpired:
                current_app.logger.warning("systemctl reload timed out, but logging config was saved")
                return True
            except Exception as e:
                # Non-critical - config was still written
                current_app.logger.warning(f"Could not reload dnsmasq, but logging config was saved: {str(e)}")
                return True
        except Exception as e:
            current_app.logger.error(f"Error enabling dnsmasq logging: {str(e)}")
            return False
    
    def start_log_monitor(self, update_interval_seconds=10):
        """Start background thread to monitor and parse dnsmasq logs"""
        try:
            def monitor_logs():
                while True:
                    try:
                        from app import create_app
                        app = create_app()
                        with app.app_context():
                            self.parse_dnsmasq_logs()
                        time.sleep(update_interval_seconds)
                    except Exception as e:
                        current_app.logger.error(f"Error in log monitor: {str(e)}")
                        time.sleep(update_interval_seconds)
            
            # Start daemon thread
            monitor_thread = threading.Thread(target=monitor_logs, daemon=True)
            monitor_thread.start()
            current_app.logger.info(f"DNS log monitor started (interval: {update_interval_seconds}s)")
            return True
        except Exception as e:
            current_app.logger.error(f"Error starting DNS log monitor: {str(e)}")
            return False


class DNSInterceptor:
    """Tries to intercept DNS queries and handle blocking at DNS level"""
    
    def __init__(self):
        self.dns_manager = DNSFilterManager()
    
    def process_query(self, client_ip, query_domain, query_type='A'):
        """Process an incoming DNS query
        
        This would be called from a low-level DNS interceptor (e.g., using libdnet or eBPF)
        For now, we mainly log and check filters
        """
        try:
            # Check if domain should be blocked
            is_blocked, matched_filter = self.dns_manager.match_domain_against_filters(query_domain)
            
            # Log the query
            self.dns_manager.log_dns_query(
                client_ip=client_ip,
                query_domain=query_domain,
                query_type=query_type,
                was_blocked=is_blocked,
                blocked_by_filter_id=matched_filter.id if matched_filter else None
            )
            
            if is_blocked:
                # Return NXDOMAIN or 127.0.0.1 response
                return {
                    'blocked': True,
                    'response_ip': '127.0.0.1',
                    'response_code': 'NXDOMAIN'
                }
            else:
                return {
                    'blocked': False,
                    'response_code': 'NOERROR'
                }
        except Exception as e:
            from flask import current_app
            current_app.logger.error(f"Error processing DNS query: {str(e)}")
            return {
                'blocked': False,
                'response_code': 'SERVFAIL'
            }


# Global instance
dns_log_parser = None

def get_dns_log_parser():
    """Get or create DNS log parser instance"""
    global dns_log_parser
    if dns_log_parser is None:
        dns_log_parser = DNSLogParser()
    return dns_log_parser
