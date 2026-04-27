import requests
import re
from flask import current_app
from app import db
from app.models import DNSBlockList, DomainFilterGroup, DomainFilter
from datetime import datetime

class BlocklistManager:
    """Manages loading and updating blocklists from external sources"""
    
    # Popular blocklist sources similar to Pi-hole
    DEFAULT_BLOCKLISTS = [
        {
            'name': 'Steven Black Hosts (Ads)',
            'url': 'https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts',
            'category': 'ads',
            'description': 'Consolidated hosts file from Steven Black blocklist'
        },
        {
            'name': 'AdServers Blocklist',
            'url': 'https://raw.githubusercontent.com/StevenBlack/hosts/master/extensions/porn/hosts',
            'category': 'ads',
            'description': 'Advertising servers blocklist'
        },
        {
            'name': 'Malware Domain List',
            'url': 'https://www.malwaredomainlist.com/hostslist/hosts.txt',
            'category': 'malware',
            'description': 'Known malware domain blocklist'
        },
        {
            'name': 'Easy Privacy Tracking Domains',
            'url': 'https://easylist.to/easylist/easylist.txt',
            'category': 'tracking',
            'description': 'Tracking and analytics domains'
        },
    ]
    
    def __init__(self):
        self.request_timeout = 30  # seconds
    
    def add_default_blocklists(self):
        """Add default blocklists to the system"""
        try:
            for blocklist_data in self.DEFAULT_BLOCKLISTS:
                # Check if already exists
                existing = DNSBlockList.query.filter_by(
                    name=blocklist_data['name']
                ).first()
                
                if not existing:
                    blocklist = DNSBlockList(
                        name=blocklist_data['name'],
                        description=blocklist_data['description'],
                        url=blocklist_data['url'],
                        category=blocklist_data['category'],
                        enabled=True
                    )
                    db.session.add(blocklist)
            
            db.session.commit()
            return True
        except Exception as e:
            current_app.logger.error(f"Error adding default blocklists: {str(e)}")
            db.session.rollback()
            return False
    
    def fetch_blocklist(self, blocklist_id):
        """Fetch and process a blocklist from URL
        
        Supports multiple formats:
        - hosts file (IP domain)
        - domain list (one per line)
        - adblock format
        - regex format
        """
        try:
            blocklist = DNSBlockList.query.get(blocklist_id)
            if not blocklist:
                raise ValueError(f"Blocklist {blocklist_id} not found")
            
            if not blocklist.enabled:
                raise ValueError(f"Blocklist {blocklist.name} is disabled")
            
            # Fetch the list
            response = requests.get(blocklist.url, timeout=self.request_timeout)
            response.raise_for_status()
            
            # Parse the list
            domains = self._parse_blocklist(response.text)
            
            # Create or update filter group
            group = DomainFilterGroup.query.filter_by(
                name=blocklist.name
            ).first()
            
            if not group:
                group = DomainFilterGroup(
                    name=blocklist.name,
                    description=blocklist.description,
                    enabled=True,
                    list_type='blocklist',
                    source_url=blocklist.url
                )
                db.session.add(group)
                db.session.flush()
            
            # Update existing filters or add new ones
            added_count = 0
            for domain in domains:
                if domain.strip():
                    existing_filter = DomainFilter.query.filter(
                        (DomainFilter.group_id == group.id) &
                        (DomainFilter.domain == domain)
                    ).first()
                    
                    if not existing_filter:
                        new_filter = DomainFilter(
                            group_id=group.id,
                            domain=domain,
                            pattern_type='exact',
                            enabled=True,
                            blocking_enabled=True
                        )
                        db.session.add(new_filter)
                        added_count += 1
            
            # Update blocklist metadata
            blocklist.domain_count = len(domains)
            blocklist.last_updated = datetime.utcnow()
            
            db.session.commit()
            
            current_app.logger.info(
                f"Loaded {added_count} new domains from {blocklist.name}"
            )
            return {
                'success': True,
                'blocklist_name': blocklist.name,
                'domains_added': added_count,
                'total_domains': len(domains)
            }
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error fetching blocklist: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _parse_blocklist(self, content):
        """Parse blocklist content in various formats
        
        Returns a set of domain names
        """
        domains = set()
        
        for line in content.split('\n'):
            line = line.strip()
            
            # Skip empty lines and comments
            if not line or line.startswith('#') or line.startswith(';'):
                continue
            
            # Skip lines with adblock format operators
            if line.startswith('[') or line.startswith('!'):
                continue
            
            # Parse hosts file format (IP domain)
            if re.match(r'^(\d+\.\d+\.\d+\.\d+|::1|::)\s+', line):
                parts = line.split()
                if len(parts) >= 2:
                    domain = parts[1]
                    domains.add(self._normalize_domain(domain))
            
            # Parse adblock format (|domain|)
            elif line.startswith('||') and line.endswith('|'):
                domain = line[2:-1]
                domains.add(self._normalize_domain(domain))
            
            # Parse plain domain list
            elif self._is_valid_domain(line):
                domains.add(self._normalize_domain(line))
        
        return domains
    
    def _normalize_domain(self, domain):
        """Normalize domain name"""
        # Remove trailing dot if present
        domain = domain.rstrip('.')
        # Convert to lowercase
        domain = domain.lower()
        # Remove www. prefix if present
        if domain.startswith('www.'):
            domain = domain[4:]
        return domain
    
    def _is_valid_domain(self, domain):
        """Check if string is a valid domain name"""
        # Basic domain validation
        pattern = r'^(?:(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)*[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)$'
        return bool(re.match(pattern, domain))
    
    def update_all_blocklists(self):
        """Update all enabled blocklists"""
        try:
            blocklists = DNSBlockList.query.filter_by(enabled=True).all()
            
            results = []
            for blocklist in blocklists:
                # Check if update is needed based on interval
                if blocklist.last_updated:
                    from datetime import timedelta
                    next_update = blocklist.last_updated + timedelta(
                        hours=blocklist.update_interval_hours
                    )
                    if datetime.utcnow() < next_update:
                        continue  # Skip if not enough time has passed
                
                result = self.fetch_blocklist(blocklist.id)
                results.append(result)
            
            return results
        except Exception as e:
            current_app.logger.error(f"Error updating blocklists: {str(e)}")
            return []
    
    def add_custom_blocklist(self, name, url, category='custom', description=''):
        """Add a custom blocklist"""
        try:
            blocklist = DNSBlockList(
                name=name,
                url=url,
                category=category,
                description=description,
                enabled=True
            )
            db.session.add(blocklist)
            db.session.commit()
            return {'success': True, 'blocklist_id': blocklist.id}
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'error': str(e)}
    
    def remove_blocklist(self, blocklist_id):
        """Remove a blocklist and all its domains"""
        try:
            blocklist = DNSBlockList.query.get(blocklist_id)
            if not blocklist:
                return {'success': False, 'error': 'Blocklist not found'}
            
            # Find associated filter group
            group = DomainFilterGroup.query.filter_by(
                name=blocklist.name
            ).first()
            
            if group:
                # Delete all filters in this group
                DomainFilter.query.filter_by(group_id=group.id).delete()
                db.session.delete(group)
            
            db.session.delete(blocklist)
            db.session.commit()
            return {'success': True}
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'error': str(e)}
    
    def get_blocklist_stats(self):
        """Get statistics about all blocklists"""
        try:
            from sqlalchemy import func
            stats = {
                'total_blocklists': DNSBlockList.query.count(),
                'enabled_blocklists': DNSBlockList.query.filter_by(enabled=True).count(),
                'total_domains': db.session.query(
                    func.sum(DomainFilter.id).label('count')
                ).select_from(DomainFilter).scalar() or 0,
                'blocklists': []
            }
            
            blocklists = DNSBlockList.query.all()
            for bl in blocklists:
                stats['blocklists'].append({
                    'id': bl.id,
                    'name': bl.name,
                    'category': bl.category,
                    'domain_count': bl.domain_count,
                    'enabled': bl.enabled,
                    'last_updated': bl.last_updated.isoformat() if bl.last_updated else None
                })
            
            return stats
        except Exception as e:
            current_app.logger.error(f"Error getting blocklist stats: {str(e)}")
            return {}
