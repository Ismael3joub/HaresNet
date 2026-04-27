#!/usr/bin/env python3
"""
DNS Filter Management Script
A utility script for testing and managing the HaresNet DNS filtering system
"""

import requests
import json
import sys
import argparse
from typing import Dict, Any, Optional
from datetime import datetime

class DNSFilterClient:
    """Client for interacting with DNS filter API"""
    
    def __init__(self, base_url: str = 'http://localhost:5000', token: Optional[str] = None):
        self.base_url = base_url
        self.api_prefix = f'{base_url}/api/dns_filter'
        self.token = token
        self.headers = {
            'Content-Type': 'application/json'
        }
        if token:
            self.headers['Authorization'] = f'Bearer {token}'
    
    def _request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make HTTP request to API"""
        url = f'{self.api_prefix}{endpoint}'
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=self.headers)
            elif method == 'POST':
                response = requests.post(url, headers=self.headers, json=data)
            elif method == 'PUT':
                response = requests.put(url, headers=self.headers, json=data)
            elif method == 'DELETE':
                response = requests.delete(url, headers=self.headers)
            else:
                raise ValueError(f'Unknown method: {method}')
            
            response.raise_for_status()
            return response.json() if response.text else {}
        except requests.exceptions.RequestException as e:
            print(f'Error: {e}')
            if hasattr(e.response, 'text'):
                print(f'Response: {e.response.text}')
            sys.exit(1)
    
    # ==================== Groups ====================
    
    def list_groups(self) -> list:
        """List all filter groups"""
        result = self._request('GET', '/groups')
        return result.get('groups', [])
    
    def create_group(self, name: str, description: str = '', list_type: str = 'blocklist',
                    source_url: str = None, enabled: bool = True) -> Dict:
        """Create a new filter group"""
        data = {
            'name': name,
            'description': description,
            'list_type': list_type,
            'enabled': enabled
        }
        if source_url:
            data['source_url'] = source_url
        
        return self._request('POST', '/groups', data)
    
    def get_group(self, group_id: int) -> Dict:
        """Get a specific group with all filters"""
        return self._request('GET', f'/groups/{group_id}')
    
    def update_group(self, group_id: int, **kwargs) -> Dict:
        """Update a filter group"""
        return self._request('PUT', f'/groups/{group_id}', kwargs)
    
    def delete_group(self, group_id: int) -> Dict:
        """Delete a filter group"""
        return self._request('DELETE', f'/groups/{group_id}')
    
    # ==================== Filters ====================
    
    def list_filters(self, group_id: int = None, enabled_only: bool = False, 
                    page: int = 1, per_page: int = 50) -> Dict:
        """List all domain filters"""
        params = f'?page={page}&per_page={per_page}'
        if group_id:
            params += f'&group_id={group_id}'
        if enabled_only:
            params += '&enabled_only=true'
        
        return self._request('GET', f'/filters{params}')
    
    def create_filter(self, group_id: int, domain: str, pattern_type: str = 'exact',
                     regex_pattern: str = None, blocking_enabled: bool = True,
                     reason: str = None, enabled: bool = True) -> Dict:
        """Create a new domain filter"""
        data = {
            'group_id': group_id,
            'domain': domain,
            'pattern_type': pattern_type,
            'blocking_enabled': blocking_enabled,
            'enabled': enabled
        }
        if regex_pattern:
            data['regex_pattern'] = regex_pattern
        if reason:
            data['reason'] = reason
        
        return self._request('POST', '/filters', data)
    
    def get_filter(self, filter_id: int) -> Dict:
        """Get a specific filter"""
        return self._request('GET', f'/filters/{filter_id}')
    
    def update_filter(self, filter_id: int, **kwargs) -> Dict:
        """Update a domain filter"""
        return self._request('PUT', f'/filters/{filter_id}', kwargs)
    
    def delete_filter(self, filter_id: int) -> Dict:
        """Delete a domain filter"""
        return self._request('DELETE', f'/filters/{filter_id}')
    
    # ==================== Blocklists ====================
    
    def list_blocklists(self) -> Dict:
        """List all blocklists"""
        return self._request('GET', '/blocklists')
    
    def add_default_blocklists(self) -> Dict:
        """Add default blocklists"""
        return self._request('POST', '/blocklists/defaults', {})
    
    def add_blocklist(self, name: str, url: str, category: str = 'custom', 
                     description: str = '') -> Dict:
        """Add a custom blocklist"""
        data = {
            'name': name,
            'url': url,
            'category': category,
            'description': description
        }
        return self._request('POST', '/blocklists', data)
    
    def fetch_blocklist(self, blocklist_id: int) -> Dict:
        """Fetch and load a blocklist"""
        return self._request('POST', f'/blocklists/{blocklist_id}/fetch', {})
    
    def update_all_blocklists(self) -> Dict:
        """Update all blocklists"""
        return self._request('POST', '/blocklists/update-all', {})
    
    def delete_blocklist(self, blocklist_id: int) -> Dict:
        """Delete a blocklist"""
        return self._request('DELETE', f'/blocklists/{blocklist_id}')
    
    # ==================== DNS Logs ====================
    
    def get_logs(self, page: int = 1, per_page: int = 50, blocked_only: bool = False,
                client_ip: str = None, domain: str = None, hours: int = 24) -> Dict:
        """Get DNS query logs"""
        params = f'?page={page}&per_page={per_page}&hours={hours}'
        if blocked_only:
            params += '&blocked_only=true'
        if client_ip:
            params += f'&client_ip={client_ip}'
        if domain:
            params += f'&domain={domain}'
        
        return self._request('GET', f'/logs{params}')
    
    def cleanup_logs(self, days: int = 30) -> Dict:
        """Clean up old DNS logs"""
        return self._request('POST', '/logs/cleanup', {'days': days})
    
    # ==================== Statistics ====================
    
    def get_stats(self) -> Dict:
        """Get overall filtering statistics"""
        return self._request('GET', '/stats')
    
    def get_domain_stats(self, domain: str) -> Dict:
        """Get statistics for a specific domain"""
        return self._request('GET', f'/stats/domain/{domain}')
    
    def get_top_domains(self, limit: int = 10) -> Dict:
        """Get top blocked domains"""
        return self._request('GET', f'/stats/top-domains?limit={limit}')
    
    def get_top_clients(self, limit: int = 10) -> Dict:
        """Get top DNS clients"""
        return self._request('GET', f'/stats/top-clients?limit={limit}')
    
    def get_timeline(self, hours: int = 24, interval: int = 60) -> Dict:
        """Get blocking timeline"""
        return self._request('GET', f'/stats/timeline?hours={hours}&interval={interval}')
    
    # ==================== Testing ====================
    
    def test_filter(self, domain: str) -> Dict:
        """Test if a domain would be blocked"""
        return self._request('GET', f'/test-filter/{domain}')
    
    def apply_config(self) -> Dict:
        """Apply all filter configurations to dnsmasq"""
        return self._request('POST', '/config/apply', {})


def print_table(rows: list, headers: list = None):
    """Print a formatted table"""
    if not rows:
        print('No data')
        return
    
    if headers is None and rows:
        headers = list(rows[0].keys())
    
    if headers:
        col_widths = [len(str(h)) for h in headers]
        for row in rows:
            for i, h in enumerate(headers):
                col_widths[i] = max(col_widths[i], len(str(row.get(h, ''))))
        
        # Print header
        print(' | '.join(h.ljust(col_widths[i]) for i, h in enumerate(headers)))
        print('-' * (sum(col_widths) + len(headers) * 3 - 1))
        
        # Print rows
        for row in rows:
            print(' | '.join(str(row.get(h, '')).ljust(col_widths[i]) for i, h in enumerate(headers)))


def main():
    parser = argparse.ArgumentParser(
        description='DNS Filter Management Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Initialize default blocklists
  python3 manage_dns_filter.py --token TOKEN blocklists init-defaults
  
  # List all filter groups
  python3 manage_dns_filter.py --token TOKEN groups list
  
  # Create a custom blocklist
  python3 manage_dns_filter.py --token TOKEN groups create "My Blocklist" "Custom domains"
  
  # Add a filter
  python3 manage_dns_filter.py --token TOKEN filters add 1 ads.example.com
  
  # Get statistics
  python3 manage_dns_filter.py --token TOKEN stats overall
  
  # Test if domain is blocked
  python3 manage_dns_filter.py --token TOKEN test ads.example.com
        '''
    )
    
    parser.add_argument('-t', '--token', required=True, help='JWT authentication token')
    parser.add_argument('-u', '--url', default='http://localhost:5000', help='API base URL')
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Groups commands
    groups_parser = subparsers.add_parser('groups', help='Manage filter groups')
    groups_subparsers = groups_parser.add_subparsers(dest='action', help='Group actions')
    
    groups_subparsers.add_parser('list', help='List all groups')
    create_group = groups_subparsers.add_parser('create', help='Create new group')
    create_group.add_argument('name', help='Group name')
    create_group.add_argument('description', nargs='?', default='', help='Description')
    create_group.add_argument('--type', choices=['blocklist', 'allowlist'], 
                             default='blocklist', help='List type')
    
    # Filters commands
    filters_parser = subparsers.add_parser('filters', help='Manage domain filters')
    filters_subparsers = filters_parser.add_subparsers(dest='action', help='Filter actions')
    
    filters_subparsers.add_parser('list', help='List all filters')
    add_filter = filters_subparsers.add_parser('add', help='Add new filter')
    add_filter.add_argument('group_id', type=int, help='Group ID')
    add_filter.add_argument('domain', help='Domain to filter')
    add_filter.add_argument('--type', choices=['exact', 'wildcard', 'regex'],
                           default='exact', help='Pattern type')
    add_filter.add_argument('--regex', help='Regex pattern (for regex type)')
    add_filter.add_argument('--reason', help='Reason for blocking')
    
    # Blocklists commands
    blocklists_parser = subparsers.add_parser('blocklists', help='Manage blocklists')
    blocklists_subparsers = blocklists_parser.add_subparsers(dest='action', help='Blocklist actions')
    
    blocklists_subparsers.add_parser('list', help='List all blocklists')
    blocklists_subparsers.add_parser('init-defaults', help='Initialize default blocklists')
    fetch_bl = blocklists_subparsers.add_parser('fetch', help='Fetch blocklist')
    fetch_bl.add_argument('id', type=int, help='Blocklist ID')
    
    # Statistics commands
    stats_parser = subparsers.add_parser('stats', help='View statistics')
    stats_subparsers = stats_parser.add_subparsers(dest='action', help='Statistics actions')
    stats_subparsers.add_parser('overall', help='Overall statistics')
    stats_subparsers.add_parser('top-domains', help='Top blocked domains')
    stats_subparsers.add_parser('top-clients', help='Top DNS clients')
    
    # Test command
    test_parser = subparsers.add_parser('test', help='Test filtering')
    test_parser.add_argument('domain', help='Domain to test')
    
    # Logs command
    logs_parser = subparsers.add_parser('logs', help='View DNS logs')
    logs_subparsers = logs_parser.add_subparsers(dest='action', help='Log actions')
    get_logs = logs_subparsers.add_parser('list', help='List DNS logs')
    get_logs.add_argument('--blocked-only', action='store_true', help='Only show blocked queries')
    get_logs.add_argument('--limit', type=int, default=50, help='Number of logs to show')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Create client
    client = DNSFilterClient(args.url, args.token)
    
    try:
        if args.command == 'groups':
            if args.action == 'list':
                groups = client.list_groups()
                if groups:
                    print_table([{'ID': g['id'], 'Name': g['name'], 'Type': g['list_type'],
                                 'Filters': g['filter_count'], 'Enabled': g['enabled']}
                               for g in groups])
            elif args.action == 'create':
                result = client.create_group(args.name, args.description, args.type)
                print(f"Created group: {result}")
        
        elif args.command == 'filters':
            if args.action == 'list':
                result = client.list_filters()
                if result.get('filters'):
                    filters = result['filters']
                    print_table([{'ID': f['id'], 'Domain': f['domain'], 'Type': f['pattern_type'],
                                 'Enabled': f['enabled'], 'Hits': f['hit_count']}
                               for f in filters])
            elif args.action == 'add':
                result = client.create_filter(
                    args.group_id, args.domain,
                    pattern_type=args.type,
                    regex_pattern=args.regex,
                    reason=args.reason
                )
                print(f"Filter added: {result}")
        
        elif args.command == 'blocklists':
            if args.action == 'list':
                result = client.list_blocklists()
                if result.get('blocklists'):
                    blocklists = result['blocklists']
                    print_table([{'ID': bl['id'], 'Name': bl['name'], 'Category': bl['category'],
                                 'Domains': bl['domain_count'], 'Enabled': bl['enabled']}
                               for bl in blocklists])
            elif args.action == 'init-defaults':
                result = client.add_default_blocklists()
                print(result)
            elif args.action == 'fetch':
                result = client.fetch_blocklist(args.id)
                print(json.dumps(result, indent=2))
        
        elif args.command == 'stats':
            if args.action == 'overall':
                stats = client.get_stats()
                print(f"Total Queries Today: {stats.get('total_queries_today', 0)}")
                print(f"Blocked Today: {stats.get('total_blocked_today', 0)}")
                print(f"Active Filters: {stats.get('total_active_filters', 0)}")
                print(f"\nTop Blocked Domains:")
                for domain in stats.get('top_blocked_domains', []):
                    print(f"  {domain['domain']}: {domain['blocked_count']} blocks")
            elif args.action == 'top-domains':
                result = client.get_top_domains(10)
                print_table(result.get('domains', []))
            elif args.action == 'top-clients':
                result = client.get_top_clients(10)
                print_table(result.get('clients', []))
        
        elif args.command == 'test':
            result = client.test_filter(args.domain)
            print(f"Domain: {result['domain']}")
            print(f"Would be blocked: {result['would_be_blocked']}")
            if result['matched_filter']:
                print(f"Matched filter: {result['matched_filter']['domain']}")
        
        elif args.command == 'logs':
            if args.action == 'list':
                result = client.get_logs(per_page=args.limit, blocked_only=args.blocked_only)
                if result.get('logs'):
                    logs = result['logs']
                    print_table([{'Time': log['timestamp'][-8:], 'Client': log['client_ip'],
                                 'Domain': log['query_domain'], 'Blocked': log['was_blocked']}
                               for log in logs])
    
    except Exception as e:
        print(f'Error: {e}', file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
