from app import create_app, db
from app.models import DomainFilter, DomainFilterGroup
from app.services.dns_filter_manager import DNSFilterManager

def debug_matching():
    app = create_app()
    with app.app_context():
        print("Checking filter for doubleclick.net...")
        filters = DomainFilter.query.all()
        target_filter = None
        for f in filters:
            if 'doubleclick' in f.domain:
                target_filter = f
                print(f"Found filter: ID={f.id}, Domain={f.domain}, Type={f.pattern_type}, Enabled={f.enabled}, Blocking={f.blocking_enabled}, GroupID={f.group_id}")
                
        if target_filter:
            group = DomainFilterGroup.query.get(target_filter.group_id)
            print(f"Group: ID={group.id}, Name={group.name}, Type={group.list_type}, Enabled={group.enabled}")
            
        manager = DNSFilterManager()
        is_blocked, matched_filter = manager.match_domain_against_filters('sub.doubleclick.net')
        print(f"Match result for 'sub.doubleclick.net': Blocked={is_blocked}, Filter={matched_filter}")

        is_blocked, matched_filter = manager.match_domain_against_filters('doubleclick.net')
        print(f"Match result for 'doubleclick.net': Blocked={is_blocked}, Filter={matched_filter}")

if __name__ == "__main__":
    debug_matching()
