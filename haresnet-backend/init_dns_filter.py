#!/usr/bin/env python3
"""
Initialize DNS filter system with default data
"""
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app, db
from app.models import DomainFilterGroup, DomainFilter, DNSBlockList
from app.services.blocklist_manager import BlocklistManager

app = create_app()

def init_dns_filter():
    """Initialize DNS filter with default groups and filters"""
    with app.app_context():
        print("Initializing DNS Filter System...")
        
        # 1. Create default blocklist group
        print("\n1. Creating default Blocklist group...")
        blocklist_group = DomainFilterGroup.query.filter_by(
            name='Default Blocklist'
        ).first()
        
        if not blocklist_group:
            blocklist_group = DomainFilterGroup(
                name='Default Blocklist',
                description='Default blocklist for ads, malware, and tracking',
                list_type='blocklist',
                enabled=True
            )
            db.session.add(blocklist_group)
            db.session.commit()
            print(f"✓ Created blocklist group: {blocklist_group.name}")
        else:
            print(f"✓ Blocklist group already exists: {blocklist_group.name}")
        
        # 2. Create default allowlist group
        print("\n2. Creating default Allowlist group...")
        allowlist_group = DomainFilterGroup.query.filter_by(
            name='Whitelist'
        ).first()
        
        if not allowlist_group:
            allowlist_group = DomainFilterGroup(
                name='Whitelist',
                description='Whitelisted domains that should always be allowed',
                list_type='allowlist',
                enabled=True
            )
            db.session.add(allowlist_group)
            db.session.commit()
            print(f"✓ Created allowlist group: {allowlist_group.name}")
        else:
            print(f"✓ Allowlist group already exists: {allowlist_group.name}")
        
        # 3. Add some example filters to blocklist group
        print("\n3. Adding example domain filters...")
        example_filters = [
            {
                'group_id': blocklist_group.id,
                'domain': 'ads.google.com',
                'pattern_type': 'exact',
                'reason': 'Google ads server',
            },
            {
                'group_id': blocklist_group.id,
                'domain': '*.doubleclick.net',
                'pattern_type': 'wildcard',
                'reason': 'DoubleClick advertising network',
            },
            {
                'group_id': blocklist_group.id,
                'domain': '^tracker[0-9]+\.example\.com$',
                'pattern_type': 'regex',
                'regex_pattern': '^tracker[0-9]+\.example\.com$',
                'reason': 'Example tracking domains (regex)',
            },
            {
                'group_id': blocklist_group.id,
                'domain': 'analytics.google.com',
                'pattern_type': 'exact',
                'reason': 'Google Analytics',
            },
            {
                'group_id': blocklist_group.id,
                'domain': 'facebook.com',
                'pattern_type': 'exact',
                'reason': 'Facebook',
            },
        ]
        
        added_count = 0
        for filter_data in example_filters:
            existing = DomainFilter.query.filter_by(
                group_id=filter_data['group_id'],
                domain=filter_data['domain']
            ).first()
            
            if not existing:
                dns_filter = DomainFilter(**filter_data)
                db.session.add(dns_filter)
                added_count += 1
        
        db.session.commit()
        print(f"✓ Added {added_count} example filters to {blocklist_group.name}")
        
        # 4. Add whitelist examples
        print("\n4. Adding whitelist examples...")
        whitelist_examples = [
            {
                'group_id': allowlist_group.id,
                'domain': 'safe.google.com',
                'pattern_type': 'exact',
                'reason': 'Safe Google service',
            },
            {
                'group_id': allowlist_group.id,
                'domain': '*.github.com',
                'pattern_type': 'wildcard',
                'reason': 'GitHub and subdomains',
            },
        ]
        
        whitelist_added = 0
        for filter_data in whitelist_examples:
            existing = DomainFilter.query.filter_by(
                group_id=filter_data['group_id'],
                domain=filter_data['domain']
            ).first()
            
            if not existing:
                dns_filter = DomainFilter(**filter_data)
                db.session.add(dns_filter)
                whitelist_added += 1
        
        db.session.commit()
        print(f"✓ Added {whitelist_added} whitelist examples")
        
        # 5. Fetch blocklists (optional - can be done separately)
        print("\n5. Blocklists setup...")
        blocklists = DNSBlockList.query.all()
        print(f"✓ {len(blocklists)} blocklists ready to be fetched")
        print("  (Blocklists will be fetched in background)")
        print("  (You can manually fetch them from the UI)")
        
        # 6. Summary
        print("\n" + "="*50)
        print("DNS Filter Initialization Complete!")
        print("="*50)
        
        filter_count = DomainFilter.query.count()
        group_count = DomainFilterGroup.query.count()
        blocklist_domains = sum(b.domain_count for b in blocklists)
        
        print(f"\nSystem Statistics:")
        print(f"  • Filter Groups: {group_count}")
        print(f"  • Individual Filters: {filter_count}")
        print(f"  • Total Blocklist Domains: {blocklist_domains}")
        print(f"  • Total Blocklists: {len(blocklists)}")
        
        print("\nNext steps:")
        print("  1. Open the frontend and go to DNS Filter page")
        print("  2. Click on 'Blocklists' tab to view loaded domains")
        print("  3. Click on 'Groups' tab to see filter groups")
        print("  4. Click on 'Filters' tab to see individual filters")
        print("  5. Try the 'Test' tab to test domain filtering")

if __name__ == '__main__':
    init_dns_filter()
