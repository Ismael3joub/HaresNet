"""
HaresNet DNS Filtering System - Architecture Diagram

┌─────────────────────────────────────────────────────────────────────────────┐
│                           EXTERNAL SOURCES                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  Blocklist URLs        dnsmasq Logs          Upstream DNS Servers            │
│  (github, etc)         (/var/log/)           (8.8.8.8, etc)                  │
│  │                     │                     │                               │
│  └──────────┬──────────┴──────────┬──────────┘                               │
│             │                     │                                           │
└─────────────┼─────────────────────┼─────────────────────────────────────────┘
              │                     │
              ▼                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        HaresNet Backend Services                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    BlocklistManager Service                          │  │
│  │  ├─ fetch_blocklist()      - Download from URL                      │  │
│  │  ├─ _parse_blocklist()     - Multi-format parser                    │  │
│  │  ├─ update_all_blocklists()- Scheduled updates (24h)                │  │
│  │  └─ get_blocklist_stats()  - Statistics                             │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│           ▲                                ▼                                │
│           │                         Stores in:                              │
│  ◀────────┘                                                                 │
│  │                                  DNSBlockList table                      │
│  │                                  DomainFilter table                      │
│  │                                                                           │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    DNSFilterManager Service                          │  │
│  │  ├─ match_domain_against_filters()    - Check if blocked             │  │
│  │  ├─ apply_blocklist_to_dnsmasq()     - Generate rules                │  │
│  │  ├─ apply_allowlist_to_dnsmasq()     - Generate rules                │  │
│  │  ├─ log_dns_query()                  - Log to database               │  │
│  │  ├─ get_filter_stats()               - Aggregate stats               │  │
│  │  └─ restart_dnsmasq()                - Apply changes                 │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│           ▲                                ▼                                │
│           │                         Stores in:                              │
│  ◀────────┘                                                                 │
│  │                                  DNSQueryLog table                       │
│  │                                  DNSDomainStat table                     │
│  │                                                                           │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                     DNSLogParser Service                             │  │
│  │  ├─ parse_dnsmasq_logs()      - Read & parse logs                   │  │
│  │  ├─ enable_logging_in_dnsmasq()- Configure dnsmasq                  │  │
│  │  ├─ start_log_monitor()       - Background monitoring               │  │
│  │  └─ process_query()           - Process individual query            │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│           ▲                                                                  │
│           │                          Calls:                                 │
│  ◀────────┴──────────────────────── DNSFilterManager                        │
│                                                                               │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                     DNS Filter API (30+ endpoints)                   │  │
│  │  /groups, /filters, /blocklists, /logs, /stats, /test-filter        │  │
│  │  (All require JWT authentication)                                    │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│           ▲                                                                  │
│           │                                                                  │
│           └─────────────────────────────────────────────────────────────┐  │
│                                                                          │   │
│  Background Jobs (Scheduled):                                           │   │
│  ├─ dns_log_parsing_job()    (30s interval)  ───┘                       │   │
│  ├─ blocklist_update_job()   (24h interval)  ──┘                        │   │
│  └─ dns_log_cleanup_job()    (daily)         ──┘                        │   │
│                                                                           │   │
└─────────────────────────────────────────────────────────────────────────┼───┘
                                                                            │
                    ┌───────────── Database –────────────┐                │
                    │ (SQLite with WAL mode)             │                │
                    │  ├─ DomainFilterGroup              │                │
                    │  ├─ DomainFilter                   │                │
                    │  ├─ DNSQueryLog (indexed)          │◀───────────────┘
                    │  ├─ DNSDomainStat                  │
                    │  └─ DNSBlockList                   │
                    └────────────────────────────────────┘

                                       ▼

              /etc/dnsmasq.d/generated-configs
              ├─ blocklist.conf   (address=/domain/127.0.0.1)
              ├─ allowlist.conf   (server=/domain/#)
              ├─ addn_hosts       (127.0.0.1 domain format)
              └─ dns-filter.conf  (general settings)

                                       ▼

                            ┌──────────────────────┐
                            │   dnsmasq Service    │
                            │  (DNS/DHCP Server)   │
                            └──────────────────────┘
                                       ▲
                                       │
                     ┌─────────────────┼─────────────────┐
                     │                 │                 │
                  Device 1          Device 2          Device 3
               192.168.1.100      192.168.1.101      192.168.1.102
            
                     │                 │                 │
                     └─────────────────┼─────────────────┘
                                       │
                            DNS Queries & Responses
                            (Blocked or Allowed)


═══════════════════════════════════════════════════════════════════════════════

DATA FLOW: DNS Query Path
═══════════════════════════════════════════════════════════════════════════════

Device makes query to "ads.example.com"
    │
    ▼
dnsmasq receives query (port 53)
    │
    ├─ Check /etc/dnsmasq.d/allowlist.conf
    │  ├─ Match found? → Forward to upstream (ALLOW)
    │  └─ No match? → Continue checking
    │
    ├─ Check /etc/dnsmasq.d/blocklist.conf
    │  ├─ Match found? → Return 127.0.0.1 (BLOCK)
    │  └─ No match? → Continue
    │
    └─ No match in any rules? → Forward to upstream DNS server
        │
        ▼
    Upstream DNS responds with IP
        │
        ▼
    dnsmasq returns IP to device
        │
        ▼
    Log entry written to /var/log/dnsmasq.log
        │
        ▼ (every 30 seconds)
DNS Log Parser reads new entries
    │
    ├─ Parse: IP, domain, response
    ├─ Check against filters
    ├─ Store in DNSQueryLog
    ├─ Update DNSDomainStat
    └─ Done!

═══════════════════════════════════════════════════════════════════════════════

DATA FLOW: Blocklist Update Path
═══════════════════════════════════════════════════════════════════════════════

Admin requests: POST /api/dns_filter/blocklists/1/fetch
    │
    ▼
BlocklistManager.fetch_blocklist(blocklist_id)
    │
    ├─ Get blocklist URL from database
    ├─ Download from GitHub/other source
    ├─ Parse content (hosts, adblock, plain text format)
    ├─ Extract domain names
    │
    ▼
Create/update DomainFilterGroup
    │
    ▼
Bulk insert DomainFilter records
    ├─ 1 record per domain
    ├─ Set pattern_type='exact'
    ├─ Set blocking_enabled=True
    │
    ▼
DNSFilterManager.apply_blocklist_to_dnsmasq()
    │
    ├─ Read all active filters from database
    ├─ Generate /etc/dnsmasq.d/blocklist.conf
    │  (each line: address=/domain/127.0.0.1)
    │
    ▼
DNSFilterManager.restart_dnsmasq()
    │
    ├─ systemctl restart dnsmasq
    │
    ▼
Filtering now active for new domains!

═══════════════════════════════════════════════════════════════════════════════

API DATABASE RELATIONSHIPS
═══════════════════════════════════════════════════════════════════════════════

User
  │
  └─── (admin only)

Device
  │
  ├─── DNS Logs (DNSQueryLog) [one-to-many]
  │    └─ Track queries from this device
  │
  └─── Filter Groups (via device_domain_filters) [many-to-many]
       └─ Future: per-device filtering

DomainFilterGroup
  │
  └─── DomainFilter [one-to-many]
       │
       ├─ Set pattern_type: exact, wildcard, regex
       ├─ Enable/disable blocking individual tokens
       │
       └─── DNSQueryLog [one-to-many]
            └─ which queries matched this filter

DNSBlockList (external sources)
  │
  └─── Associated with DomainFilterGroup
       (identifies source of filters)

DNSQueryLog
  │
  ├─── blocked_by_filter_id (FK to DomainFilter)
  │    └─ Which filter blocked this query
  │
  ├─── device_id (FK to Device)
  │    └─ Which device made the query
  │
  └─── Associated DNSDomainStat
       └─ updates statistics

DNSDomainStat (aggregate statistics)
  │
  └─── Updated from DNSQueryLog
       └─ query_count, blocked_count, category

═══════════════════════════════════════════════════════════════════════════════

FILE STRUCTURE
═══════════════════════════════════════════════════════════════════════════════

app/
├─ models.py                           (NEW: 6 models added)
│
├─ api/
│  └─ dns_filter.py                   (NEW: 30+ endpoints)
│
└─ services/
   ├─ dns_filter_manager.py           (NEW: Core filtering)
   ├─ blocklist_manager.py            (NEW: Blocklist loading)
   ├─ dns_log_parser.py               (NEW: Log parsing)
   └─ ... (existing services)

Root/
├─ manage_dns_filter.py               (NEW: CLI tool)
├─ DNS_FILTER_README.md               (NEW: Full docs)
├─ QUICKSTART_DNS_FILTER.md           (NEW: Getting started)
├─ DNS_FILTERING_IMPLEMENTATION...md  (NEW: This overview)
│
├─ app/__init__.py                    (MODIFIED: Register blueprint)
├─ config.py                          (MODIFIED: Add DNS config)
└─ run.py                             (MODIFIED: Add background jobs)

dnsmasq config (auto-generated):
/etc/dnsmasq.d/
├─ blocklist.conf         (address=/domain/127.0.0.1)
├─ allowlist.conf         (server=/domain/#)
├─ addn_hosts             (127.0.0.1 domain format)
└─ dns-filter.conf        (settings)

Logs:
/var/log/
└─ dnsmasq.log            (parsed every 30 seconds)

═══════════════════════════════════════════════════════════════════════════════
"""

print(__doc__)
