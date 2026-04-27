import socket
import threading
import time
import struct
import select
from app import db, create_app, socketio
from app.services.dns_filter_manager import DNSFilterManager
from datetime import datetime
from flask import current_app

import os

class DNSProxyService:
    def __init__(self, host=None, port=53, upstream_host='127.0.0.1', upstream_port=5353):
        # Use LAN_IP if not specified, to avoid binding 0.0.0.0 which conflicts with host's systemd-resolved
        self.host = host or os.getenv('LAN_IP', '0.0.0.0')
        self.port = port
        self.upstream_host = upstream_host
        self.upstream_port = upstream_port
        self.sock = None
        self.running = False
        self.dns_manager = DNSFilterManager()
        self.app = create_app()

    def start(self):
        """Start the DNS proxy server"""
        if self.running:
            return

        # Try to bind with retries, as interface might not be up yet
        retries = 5
        for i in range(retries):
            try:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self.sock.bind((self.host, self.port))
                self.sock.setblocking(False)  # Set non-blocking for select()
                self.running = True
                
                # Start listener thread
                thread = threading.Thread(target=self._server_loop)
                thread.daemon = True
                thread.start()
                
                print(f"DNS Proxy started on {self.host}:{self.port}, forwarding to {self.upstream_host}:{self.upstream_port}")
                return True
            except OSError as e:
                # If Address already in use or Cannot assign requested address
                print(f"Failed to bind DNS Proxy on {self.host}:{self.port}: {e}. Retrying in 2s...")
                time.sleep(2)
                if i == retries - 1:
                    print(f"Could not start DNS Proxy after {retries} attempts.")
                    return False
        return False

    def stop(self):
        """Stop the DNS proxy server"""
        self.running = False
        if self.sock:
            self.sock.close()

    def _server_loop(self):
        """Main server loop to handle incoming DNS requests"""
        # Start logging worker
        self.log_queue = []
        self.last_log_flush = time.time()
        threading.Thread(target=self._logging_worker, daemon=True).start()
        
        while self.running:
            try:
                ready = select.select([self.sock], [], [], 1.0)
                if ready[0]:
                    data, addr = self.sock.recvfrom(4096)
                    threading.Thread(target=self._handle_request, args=(data, addr)).start()
            except Exception as e:
                if self.running:
                    print(f"Error in DNS proxy loop: {e}")

    def _logging_worker(self):
        """Background worker to batch DNS logs and update DB periodically"""
        while self.running:
            try:
                if self.log_queue and (len(self.log_queue) >= 50 or time.time() - self.last_log_flush > 5):
                    batch = []
                    # Thread-safe pop (basic approach for brevity)
                    while self.log_queue and len(batch) < 100:
                        batch.append(self.log_queue.pop(0))
                    
                    if batch:
                        with self.app.app_context():
                            self.dns_manager.log_dns_queries_batch(batch)
                            self.last_log_flush = time.time()
                
                time.sleep(1)
            except Exception as e:
                print(f"Error in DNS logging worker: {e}")
                time.sleep(2)

    def _handle_request(self, data, client_addr):
        """Process a single DNS request"""
        try:
            domain, query_type_int = self._parse_dns_packet(data)
            query_type = self._get_type_name(query_type_int)
            
            if not domain:
                response = self._forward_query(data)
                if response: self.sock.sendto(response, client_addr)
                return

            # Check filters (read-only mostly, but uses DB)
            with self.app.app_context():
                is_blocked, matched_filter = self.dns_manager.match_domain_against_filters(domain)
                
                # Queue the log instead of writing immediately
                self.log_queue.append({
                    'client_ip': client_addr[0],
                    'query_domain': domain,
                    'query_type': query_type,
                    'was_blocked': is_blocked,
                    'blocked_by_filter_id': matched_filter.id if matched_filter else None,
                    'timestamp': datetime.utcnow()
                })

                # Push real-time update (lightweight)
                try:
                    socketio.emit('new_dns_log', {
                        'timestamp': datetime.utcnow().isoformat(),
                        'client_ip': client_addr[0],
                        'domain': domain,
                        'type': query_type,
                        'status': 'BLOCKED' if is_blocked else 'ALLOWED',
                        'filter': matched_filter.name if matched_filter else None
                    })
                except Exception: pass

                if is_blocked:
                    # Construct valid NXDOMAIN or refused response
                    # For simplicity, we can sometimes just return an empty response or constructing a proper header
                    # A proper blocking response requires constructing a valid DNS packet.
                    # Simplest valid blocking response is NXDOMAIN (Response Code 3)
                    
                    # Transaction ID (2 bytes)
                    tid = data[:2]
                    # Flags (2 bytes): Standard query response (0x81), NXDOMAIN (0x83 for last nibble 3=NXDOMAIN)
                    # 0x8183 = Response, Recursion Available, NXDOMAIN
                    flags = b'\x81\x83' 
                    # QDCOUNT (2 bytes) - Copy from request (usually 1)
                    qdcount = data[4:6]
                    # ANCOUNT (2 bytes) - 0
                    ancount = b'\x00\x00'
                    # NSCOUNT (2 bytes) - 0
                    nscount = b'\x00\x00'
                    # ARCOUNT (2 bytes) - 0
                    arcount = b'\x00\x00'
                    
                    # Payload: Original query section
                    # The end of the query section is determined by parsing, but we can just copy the whole packet if it's simple
                    # Or simpler: return header + question + empty answer.
                    # We already parsed domain, so we know where question ends roughly, but let's just use the original Question section.
                    # This is a bit hacky, constructing a minimal valid response is safer.
                    
                    response = tid + flags + qdcount + ancount + nscount + arcount + data[12:]
                    self.sock.sendto(response, client_addr)
                    
                    # Send notification
                    self._send_blocking_notification(client_addr[0], domain, matched_filter)
                    return

            # If not blocked, forward to upstream
            response = self._forward_query(data)
            if response:
                self.sock.sendto(response, client_addr)

        except Exception as e:
            print(f"Error handling DNS request from {client_addr}: {e}")

    def _forward_query(self, data):
        """Forward DNS query to upstream DNS server"""
        try:
            upstream_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            upstream_sock.settimeout(2.0)
            upstream_sock.sendto(data, (self.upstream_host, self.upstream_port))
            response, _ = upstream_sock.recvfrom(4096)
            upstream_sock.close()
            return response
        except Exception as e:
            # print(f"Upstream DNS error: {e}")
            return None

    def _parse_dns_packet(self, data):
        """
        Extract domain name and query type from DNS packet
        Returns (domain_name, query_type_int)
        """
        try:
            # Header is 12 bytes
            if len(data) < 12:
                return None, 0
                
            # Question section starts at byte 12
            idx = 12
            parts = []
            while idx < len(data):
                length = data[idx]
                if length == 0:
                    break
                # Handle compression pointers (0xC0) if present (unlikely in query, but possible)
                if (length & 0xC0) == 0xC0:
                    # Pointer compression updates idx to end
                    idx += 2
                    break 
                
                idx += 1
                parts.append(data[idx:idx+length].decode('utf-8', errors='ignore'))
                idx += length
            
            domain = '.'.join(parts)
            
            # After domain name (and 0x00 byte), we have Type (2 bytes) and Class (2 bytes)
            # idx is now at the 0x00 terminator
            idx += 1
            if idx + 4 <= len(data):
                qtype = struct.unpack('!H', data[idx:idx+2])[0]
                return domain, qtype
            
            return domain, 0
        except Exception:
            return None, 0

    def _get_type_name(self, type_int):
        """Convert DNS type integer to string"""
        types = {
            1: 'A',
            2: 'NS',
            5: 'CNAME',
            6: 'SOA',
            12: 'PTR',
            15: 'MX',
            16: 'TXT',
            28: 'AAAA',
            33: 'SRV',
        }
        return types.get(type_int, f"TYPE{type_int}")

    def _get_client_info(self, client_ip):
        """Get client MAC and Name from DB or ARP"""
        client_mac = "Unknown"
        client_name = "Unknown"
        
        # Try DB first
        try:
            from app.models import Device
            with self.app.app_context():
                device = Device.query.filter_by(ip=client_ip).first()
                if device:
                    client_mac = device.mac
                    client_name = device.hostname or device.label or "Unknown"
        except Exception as e:
            print(f"Error getting client info from DB: {e}")
            
        # If not found in DB or MAC is unknown, try ARP (if locally reachable)
        if client_mac == "Unknown":
            try:
                # Read /proc/net/arp
                with open('/proc/net/arp', 'r') as f:
                    for line in f.readlines()[1:]:
                        parts = line.split()
                        if len(parts) >= 4 and parts[0] == client_ip:
                            client_mac = parts[3]
                            break
            except Exception:
                pass
                
        return client_mac, client_name

    def _send_blocking_notification(self, client_ip, domain, matched_filter):
        """Send notification via ntfy"""
        try:
            import requests
            ntfy_url = os.getenv('NTFY_URL', 'https://ntfy.sh')
            ntfy_topic = os.getenv('NTFY_TOPIC', 'haresnet_alerts')
            
            if not ntfy_topic:
                return

            client_mac, client_name = self._get_client_info(client_ip)
            filter_name = matched_filter.group.name if matched_filter and matched_filter.group else "Unknown Filter"
            
            message = f"Blocked access to {domain}\nClient: {client_ip} ({client_name})\nMAC: {client_mac}\nFilter: {filter_name}"
            
            full_url = f"{ntfy_url}/{ntfy_topic}"
            
            print(f"Sending notification to {full_url}: {message}")
            
            requests.post(full_url,
                data=message,
                headers={
                    "Title": "HaresNet DNS Blocked",
                    "Priority": "high",
                    "Tags": "no_entry_sign,shield"
                },
                timeout=5
            )
        except Exception as e:
            print(f"Failed to send ntfy notification: {e}")
