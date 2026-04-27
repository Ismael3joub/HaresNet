# DNS Query Logs - Fix Summary

## Problem
Your DNS Query Logs table showed empty **Domain** and **Group** columns:
- Timestamp: ✓ Populated
- Domain: ❌ Blank
- Client IP: ✓ Populated  
- Status: ❌ Blank/Not shown
- Type: ✓ Populated
- Group: ✓ Shows "-"

## Root Causes Found & Fixed

### 1. **Missing Frontend-Friendly Fields** 
   - **File**: `app/models.py` (DNSQueryLog.to_dict method)
   - **Issue**: API returned `query_domain` but frontend might expect `domain`
   - **Fix**: Added direct `domain` alias field to API response

### 2. **Missing Status Display**
   - **Issue**: No readable status (ALLOWED/BLOCKED) in response
   - **Fix**: Added `status` field that converts boolean to "ALLOWED" or "BLOCKED"

### 3. **Group Data Only on Blocked Queries**
   - **Issue**: `matched_group` was `None` for allowed queries
   - **Fix**: Enhanced logic to show device group for allowed queries and filter group for blocked

### 4. **DNS Log Parser Regex Issues**
   - **File**: `app/services/dns_log_parser.py`
   - **Issue**: Single regex pattern might not match all dnsmasq log formats
   - **Fix**: Added backup regex pattern to handle variations in dnsmasq output

## Changes Made

### `app/models.py` (DNSQueryLog.to_dict method)
```python
# NEW FIELDS ADDED:
'domain': self.query_domain,              # Direct alias for UI
'status': 'BLOCKED' if self.was_blocked else 'ALLOWED',  # Readable status
'group': device_group,                    # Device group name
'matched_group': matched_group            # Filter group or fallback to device group
```

### `app/services/dns_log_parser.py`
- Added `query_alt` regex pattern for flexible dnsmasq log parsing
- Enhanced `_parse_query_line()` to try both patterns

## Result
After these changes:
- ✓ **Domain** column will display query domains
- ✓ **Status** column will show "ALLOWED" or "BLOCKED"  
- ✓ **Group** column will show device group or filter group
- ✓ Better parsing of various dnsmasq log formats

## Testing
Run the test script to verify:
```bash
python3 test_log_fix.py
```

Or test the API directly:
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:5000/api/dns-filter/logs
```

Look for these fields in the JSON response:
- `domain` (new)
- `status` (new)
- `matched_group` (improved)

## Next Steps
1. Restart the haresnet-router service
2. Generate new DNS queries (browse to a website)
3. Check the logs table - Domain and Group columns should now be populated!
