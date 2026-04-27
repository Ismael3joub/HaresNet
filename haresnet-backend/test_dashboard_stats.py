#!/usr/bin/env python3
"""
Test DNS Filtering Stats - Verify Dashboard Data Works
"""
import sys
import json

def test_stats():
    """Test DNS filtering statistics endpoints"""
    print("\n" + "="*70)
    print("Testing DNS Filtering Dashboard Stats")
    print("="*70)
    
    try:
        sys.path.insert(0, '/home/super/Desktop/New Folder 1/ismael/haresnet-backend')
        
        from app import create_app, db
        from app.models import DomainFilter, DomainFilterGroup, DNSQueryLog
        from datetime import datetime, timedelta
        
        app = create_app()
        
        with app.app_context():
            print("\n✓ Flask app initialized")
            
            # Check database contents
            print("\n1️⃣  Current Database State:")
            
            total_queries = DNSQueryLog.query.count()
            blocked_queries = DNSQueryLog.query.filter_by(was_blocked=True).count()
            allowed_queries = total_queries - blocked_queries
            
            active_filters = DomainFilter.query.filter_by(enabled=True, blocking_enabled=True).count()
            total_filters = DomainFilter.query.count()
            
            # Use try-except for blocklists query due to potential schema issues
            try:
                from sqlalchemy import func as sqlfunc
                blocklists = db.session.query(sqlfunc.count(DomainFilterGroup.id)).filter(
                    DomainFilterGroup.enabled == True,
                    DomainFilterGroup.list_type == 'blocklist'
                ).scalar() or 0
            except Exception as db_err:
                print(f"   ⚠ Database query note: {str(db_err)[:50]}")
                blocklists = 0
            
            print(f"   Total DNS Queries: {total_queries}")
            print(f"   Blocked Queries: {blocked_queries}")
            print(f"   Allowed Queries: {allowed_queries}")
            print(f"   Active Filters: {active_filters}/{total_filters}")
            print(f"   Blocklists: {blocklists}")
            
            # Get today's stats
            print("\n2️⃣  Today's Statistics:")
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            
            today_queries = DNSQueryLog.query.filter(
                DNSQueryLog.timestamp >= today_start
            ).count()
            
            today_blocked = DNSQueryLog.query.filter(
                (DNSQueryLog.was_blocked == True) &
                (DNSQueryLog.timestamp >= today_start)
            ).count()
            
            today_allowed = today_queries - today_blocked
            today_block_rate = round((today_blocked / today_queries * 100), 2) if today_queries > 0 else 0
            
            print(f"   Queries Today: {today_queries}")
            print(f"   Blocked Today: {today_blocked}")
            print(f"   Allowed Today: {today_allowed}")
            print(f"   Block Rate: {today_block_rate}%")
            
            # Test the manager method
            print("\n3️⃣  Testing dns_manager.get_filter_stats():")
            from app.services.dns_filter_manager import DNSFilterManager
            dns_manager = DNSFilterManager()
            
            stats = dns_manager.get_filter_stats()
            print(f"   Stats returned: {json.dumps(stats, indent=2)}")
            
            # Test dashboard summary response format
            print("\n4️⃣  Expected Dashboard Response Format:")
            dashboard_response = {
                'summary': {
                    'queries_today': today_queries,
                    'blocked_today': today_blocked,
                    'allowed_today': today_allowed,
                    'block_rate': today_block_rate,
                    'active_filters': active_filters,
                    'total_filters': total_filters,
                    'blocklists': blocklists
                }
            }
            
            print(f"   Summary: {json.dumps(dashboard_response['summary'], indent=2)}")
            
            # Summary
            print("\n" + "="*70)
            print("API ENDPOINTS FOR DASHBOARD:")
            print("="*70)
            print("\nFor Real-Time Stats (No Auth Required):")
            print("  GET http://localhost:5000/api/dns-filter/stats/public")
            print("  Response:")
            print("  {")
            print(f"    'queries_today': {today_queries},")
            print(f"    'blocked_today': {today_blocked},")
            print(f"    'allowed_today': {today_allowed},")
            print(f"    'block_rate': {today_block_rate},")
            print(f"    'active_filters': {active_filters},")
            print(f"    'blocklists': {blocklists}")
            print("  }")
            
            print("\n\nFor Detailed Dashboard (Requires Auth):")
            print("  GET http://localhost:5000/api/dns-filter/dashboard/summary")
            print("  Headers: Authorization: Bearer YOUR_TOKEN")
            print("  Response: Complete dashboard data with timeline, top domains, etc.")
            
            print("\n" + "="*70)
            print("DASHBOARD UI USAGE:")
            print("="*70)
            print("""
To use these stats in your dashboard:

1. Call GET /api/dns-filter/stats/public every 30 seconds:
   fetch('/api/dns-filter/stats/public')
     .then(r => r.json())
     .then(data => {
       document.getElementById('queries-today').textContent = data.queries_today;
       document.getElementById('blocked-today').textContent = data.blocked_today;
       document.getElementById('allowed-today').textContent = data.allowed_today;
       document.getElementById('block-rate').textContent = data.block_rate + '%';
       document.getElementById('active-filters').textContent = data.active_filters;
       document.getElementById('blocklists').textContent = data.blocklists;
     });

2. Or for authenticated users, use /api/dns-filter/dashboard/summary for:
   - Top blocked domains
   - Top clients
   - Hourly timeline data
   - Everything from public stats

3. Auto-refresh every 30-60 seconds for live updates
""")
            
            print("\n" + "="*70)
            print("STATUS:")
            print("="*70)
            if today_queries > 0:
                print("✅ Data is being collected and is available!")
                print("   Dashboard should show live statistics")
            else:
                print("⚠️  No queries recorded yet")
                print("   Make some DNS queries to see data")
                print("   (Browse websites or use: nslookup example.com)")
            
    except Exception as e:
        print(f"\n✗ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == '__main__':
    success = test_stats()
    sys.exit(0 if success else 1)
