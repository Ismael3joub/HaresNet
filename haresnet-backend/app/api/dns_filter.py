from flask import Blueprint, jsonify, request, current_app
from flask_jwt_extended import jwt_required
from app import db
from app.models import (
    DomainFilter, DomainFilterGroup, DNSQueryLog, DNSDomainStat,
    DNSBlockList, Device
)
from app.services.dns_filter_manager import DNSFilterManager
from app.services.blocklist_manager import BlocklistManager
from datetime import datetime, timedelta
from sqlalchemy import func, desc
import json

bp = Blueprint('dns_filter', __name__)
dns_manager = DNSFilterManager()
blocklist_manager = BlocklistManager()

# Log monitoring should be started by the application factory or a dedicated service command
# to avoid circular imports and context errors during startup.

# ==================== Public Stats (No Auth Required) ====================

@bp.route('/stats/public', methods=['GET'])
def get_public_stats():
    """Get public DNS filtering statistics (real-time, no authentication required)"""
    try:
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Get today's statistics
        total_queries_today = DNSQueryLog.query.filter(
            DNSQueryLog.timestamp >= today_start
        ).count()
        
        blocked_today = DNSQueryLog.query.filter(
            (DNSQueryLog.was_blocked == True) &
            (DNSQueryLog.timestamp >= today_start)
        ).count()
        
        allowed_today = total_queries_today - blocked_today
        block_rate = round((blocked_today / total_queries_today * 100), 2) if total_queries_today > 0 else 0
        
        # Get filter counts
        active_filters = DomainFilter.query.filter(
            (DomainFilter.enabled == True) &
            (DomainFilter.blocking_enabled == True)
        ).count()
        
        blocklists = DomainFilterGroup.query.filter(
            (DomainFilterGroup.enabled == True) &
            (DomainFilterGroup.list_type == 'blocklist')
        ).count()
        
        return jsonify({
            'queries_today': total_queries_today,
            'blocked_today': blocked_today,
            'allowed_today': allowed_today,
            'block_rate': block_rate,
            'active_filters': active_filters,
            'blocklists': blocklists
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting public stats: {str(e)}")
        return jsonify({
            'queries_today': 0,
            'blocked_today': 0,
            'allowed_today': 0,
            'block_rate': 0,
            'active_filters': 0,
            'blocklists': 0,
            'error': str(e)
        }), 200  # Return 200 even on error to not break monitoring

# ==================== Filter Groups ====================

@bp.route('/groups', methods=['GET'])
@jwt_required()
def get_filter_groups():
    """Get all filter groups"""
    try:
        groups = DomainFilterGroup.query.all()
        return jsonify({
            'groups': [g.to_dict() for g in groups]
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/groups', methods=['POST'])
@jwt_required()
def create_filter_group():
    """Create a new filter group"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('name'):
            return jsonify({'error': 'Name is required'}), 400
        
        # Check if already exists
        existing = DomainFilterGroup.query.filter_by(name=data['name']).first()
        if existing:
            return jsonify({'error': 'Group with this name already exists'}), 400
        
        group = DomainFilterGroup(
            name=data['name'],
            description=data.get('description'),
            enabled=data.get('enabled', True),
            list_type=data.get('list_type', 'blocklist'),
            source_url=data.get('source_url'),
            color=data.get('color', '#64748b')
        )
        
        db.session.add(group)
        db.session.commit()
        
        return jsonify({
            'message': 'Filter group created successfully',
            'group': group.to_dict()
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/groups/<int:group_id>', methods=['GET'])
@jwt_required()
def get_filter_group(group_id):
    """Get a specific filter group with all filters"""
    try:
        group = DomainFilterGroup.query.get(group_id)
        if not group:
            return jsonify({'error': 'Group not found'}), 404
        
        group_data = group.to_dict()
        group_data['filters'] = [f.to_dict() for f in group.filters]
        
        return jsonify(group_data), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/groups/<int:group_id>', methods=['PUT'])
@jwt_required()
def update_filter_group(group_id):
    """Update a filter group"""
    try:
        group = DomainFilterGroup.query.get(group_id)
        if not group:
            return jsonify({'error': 'Group not found'}), 404
        
        data = request.get_json()
        
        if 'name' in data:
            # Check for duplicates
            existing = DomainFilterGroup.query.filter(
                (DomainFilterGroup.name == data['name']) &
                (DomainFilterGroup.id != group_id)
            ).first()
            if existing:
                return jsonify({'error': 'Group with this name already exists'}), 400
            group.name = data['name']
        
        if 'description' in data:
            group.description = data['description']
        if 'enabled' in data:
            group.enabled = data['enabled']
        if 'list_type' in data:
            group.list_type = data['list_type']
        if 'source_url' in data:
            group.source_url = data['source_url']
        if 'color' in data:
            group.color = data['color']
        
        group.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'message': 'Filter group updated successfully',
            'group': group.to_dict()
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/groups/<int:group_id>', methods=['DELETE'])
@jwt_required()
def delete_filter_group(group_id):
    """Delete a filter group and all its filters"""
    try:
        group = DomainFilterGroup.query.get(group_id)
        if not group:
            return jsonify({'error': 'Group not found'}), 404
        
        # Delete all filters in this group
        DomainFilter.query.filter_by(group_id=group_id).delete()
        
        db.session.delete(group)
        db.session.commit()
        
        # Reapply filtering rules
        dns_manager.apply_blocklist_to_dnsmasq()
        dns_manager.apply_allowlist_to_dnsmasq()
        dns_manager.restart_dnsmasq()
        
        return jsonify({'message': 'Filter group deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ==================== Domain Filters ====================

@bp.route('/filters', methods=['GET'])
@jwt_required()
def get_filters():
    """Get all domain filters with optional filtering"""
    try:
        group_id = request.args.get('group_id', type=int)
        enabled_only = request.args.get('enabled_only', 'false').lower() == 'true'
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        
        query = DomainFilter.query
        
        if group_id:
            query = query.filter_by(group_id=group_id)
        
        if enabled_only:
            query = query.filter_by(enabled=True, blocking_enabled=True)
        
        pagination = query.paginate(page=page, per_page=per_page)
        
        return jsonify({
            'filters': [f.to_dict() for f in pagination.items],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': pagination.total,
                'pages': pagination.pages
            }
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/filters', methods=['POST'])
@jwt_required()
def create_filter():
    """Create a new domain filter"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('group_id') or not data.get('domain'):
            return jsonify({'error': 'group_id and domain are required'}), 400
        
        # Validate group exists
        group = DomainFilterGroup.query.get(data['group_id'])
        if not group:
            return jsonify({'error': 'Group not found'}), 404
        
        # Validate regex pattern if pattern_type is regex
        if data.get('pattern_type') == 'regex' and data.get('regex_pattern'):
            import re
            try:
                re.compile(data['regex_pattern'])
            except re.error as e:
                return jsonify({'error': f'Invalid regex pattern: {str(e)}'}), 400
        
        filter_item = DomainFilter(
            group_id=data['group_id'],
            domain=data['domain'],
            pattern_type=data.get('pattern_type', 'exact'),
            regex_pattern=data.get('regex_pattern'),
            enabled=data.get('enabled', True),
            blocking_enabled=data.get('blocking_enabled', True),
            reason=data.get('reason')
        )
        
        db.session.add(filter_item)
        db.session.commit()
        
        # Reapply rules (don't fail the request if restart fails)
        try:
            dns_manager.apply_blocklist_to_dnsmasq()
            dns_manager.restart_dnsmasq()
        except Exception as restart_error:
            # Log the error but don't fail the API response
            from flask import current_app
            current_app.logger.warning(f"Filter created but could not restart dnsmasq: {str(restart_error)}")
        
        return jsonify({
            'message': 'Filter created successfully (note: dnsmasq restart may need manual intervention)',
            'filter': filter_item.to_dict()
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/filters/<int:filter_id>', methods=['GET'])
@jwt_required()
def get_filter(filter_id):
    """Get a specific filter"""
    try:
        filter_item = DomainFilter.query.get(filter_id)
        if not filter_item:
            return jsonify({'error': 'Filter not found'}), 404
        
        return jsonify(filter_item.to_dict()), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/filters/<int:filter_id>', methods=['PUT'])
@jwt_required()
def update_filter(filter_id):
    """Update a domain filter"""
    try:
        filter_item = DomainFilter.query.get(filter_id)
        if not filter_item:
            return jsonify({'error': 'Filter not found'}), 404
        
        data = request.get_json()
        
        if 'domain' in data:
            filter_item.domain = data['domain']
        if 'pattern_type' in data:
            filter_item.pattern_type = data['pattern_type']
        if 'regex_pattern' in data:
            filter_item.regex_pattern = data['regex_pattern']
        if 'enabled' in data:
            filter_item.enabled = data['enabled']
        if 'blocking_enabled' in data:
            filter_item.blocking_enabled = data['blocking_enabled']
        if 'reason' in data:
            filter_item.reason = data['reason']
        
        db.session.commit()
        
        # Reapply rules (don't fail the request if restart fails)
        try:
            dns_manager.apply_blocklist_to_dnsmasq()
            dns_manager.restart_dnsmasq()
        except Exception as restart_error:
            # Log the error but don't fail the API response
            from flask import current_app
            current_app.logger.warning(f"Filter updated but could not restart dnsmasq: {str(restart_error)}")
        
        return jsonify({
            'message': 'Filter updated successfully (note: dnsmasq restart may need manual intervention)',
            'filter': filter_item.to_dict()
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/filters/<int:filter_id>', methods=['DELETE'])
@jwt_required()
def delete_filter(filter_id):
    """Delete a filter"""
    try:
        filter_item = DomainFilter.query.get(filter_id)
        if not filter_item:
            return jsonify({'error': 'Filter not found'}), 404
        
        db.session.delete(filter_item)
        db.session.commit()
        
        # Reapply rules (don't fail the request if restart fails)
        try:
            dns_manager.apply_blocklist_to_dnsmasq()
            dns_manager.restart_dnsmasq()
        except Exception as restart_error:
            # Log the error but don't fail the API response
            from flask import current_app
            current_app.logger.warning(f"Filter deleted but could not restart dnsmasq: {str(restart_error)}")
        
        return jsonify({'message': 'Filter deleted successfully (note: dnsmasq restart may need manual intervention)'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ==================== Blocklists ====================

@bp.route('/blocklists', methods=['GET'])
@jwt_required()
def get_blocklists():
    """Get all blocklists"""
    try:
        blocklists = DNSBlockList.query.all()
        return jsonify({
            'blocklists': [bl.to_dict() for bl in blocklists],
            'stats': blocklist_manager.get_blocklist_stats()
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/blocklists', methods=['POST'])
@jwt_required()
def add_blocklist():
    """Add a new blocklist"""
    try:
        data = request.get_json()
        
        if not data.get('name') or not data.get('url'):
            return jsonify({'error': 'name and url are required'}), 400
        
        result = blocklist_manager.add_custom_blocklist(
            name=data['name'],
            url=data['url'],
            category=data.get('category', 'custom'),
            description=data.get('description', '')
        )
        
        if result['success']:
            return jsonify(result), 201
        else:
            return jsonify(result), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/blocklists/defaults', methods=['POST'])
@jwt_required()
def add_default_blocklists():
    """Add default blocklists"""
    try:
        blocklist_manager.add_default_blocklists()
        return jsonify({'message': 'Default blocklists added successfully'}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/blocklists/<int:blocklist_id>/fetch', methods=['POST'])
@jwt_required()
def fetch_blocklist(blocklist_id):
    """Fetch and load a blocklist from URL"""
    try:
        result = blocklist_manager.fetch_blocklist(blocklist_id)
        
        if result['success']:
            # Reapply rules after loading
            dns_manager.apply_blocklist_to_dnsmasq()
            dns_manager.restart_dnsmasq()
            return jsonify(result), 200
        else:
            return jsonify(result), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/blocklists/update-all', methods=['POST'])
@jwt_required()
def update_all_blocklists():
    """Update all blocklists"""
    try:
        results = blocklist_manager.update_all_blocklists()
        
        # Reapply rules
        dns_manager.apply_blocklist_to_dnsmasq()
        dns_manager.restart_dnsmasq()
        
        return jsonify({
            'message': 'Blocklists updated successfully',
            'results': results
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/blocklists/<int:blocklist_id>', methods=['DELETE'])
@jwt_required()
def delete_blocklist(blocklist_id):
    """Delete a blocklist"""
    try:
        result = blocklist_manager.remove_blocklist(blocklist_id)
        
        if result['success']:
            # Reapply rules
            dns_manager.apply_blocklist_to_dnsmasq()
            dns_manager.restart_dnsmasq()
            return jsonify(result), 200
        else:
            return jsonify(result), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ==================== DNS Query Logs ====================

@bp.route('/logs', methods=['GET'])
@jwt_required()
def get_dns_logs():
    """Get DNS query logs with filtering"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 100, type=int)
        blocked_only = request.args.get('blocked_only', 'false').lower() == 'true'
        client_ip = request.args.get('client_ip')
        domain = request.args.get('domain')
        hours_back = request.args.get('hours', 24, type=int)
        
        # Base query with time filter
        cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
        query = DNSQueryLog.query.filter(DNSQueryLog.timestamp >= cutoff_time)
        
        if blocked_only:
            query = query.filter_by(was_blocked=True)
        
        if client_ip:
            query = query.filter_by(client_ip=client_ip)
        
        if domain:
            if domain.startswith('/') and domain.endswith('/') and len(domain) > 2:
                # Regex search
                pattern = domain[1:-1]
                query = query.filter(DNSQueryLog.query_domain.op('REGEXP')(pattern))
            elif '*' in domain:
                # Wildcard search
                query = query.filter(DNSQueryLog.query_domain.ilike(domain.replace('*', '%')))
            else:
                # Standard contains
                query = query.filter(DNSQueryLog.query_domain.contains(domain))
        
        pagination = query.order_by(desc(DNSQueryLog.timestamp)).paginate(
            page=page,
            per_page=per_page
        )
        
        return jsonify({
            'logs': [log.to_dict() for log in pagination.items],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': pagination.total,
                'pages': pagination.pages
            }
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/logs/cleanup', methods=['POST'])
@jwt_required()
def cleanup_logs():
    """Clean up old DNS logs"""
    try:
        days = request.get_json().get('days', 30)
        deleted_count = dns_manager.cleanup_old_logs(days)
        return jsonify({
            'message': f'Cleaned up {deleted_count} old DNS logs',
            'deleted_count': deleted_count
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/logs/live', methods=['GET'])
@jwt_required()
def get_live_dns_logs():
    """Get live DNS query logs since the last timestamp."""
    try:
        last_timestamp = request.args.get('last_timestamp', None, type=str)
        if last_timestamp:
            last_timestamp = datetime.fromisoformat(last_timestamp)
        else:
            last_timestamp = datetime.utcnow() - timedelta(minutes=5)  # Default to last 5 minutes

        query = DNSQueryLog.query.filter(DNSQueryLog.timestamp > last_timestamp)
        logs = query.order_by(desc(DNSQueryLog.timestamp)).all()

        return jsonify({
            'logs': [log.to_dict() for log in logs],
            'last_timestamp': datetime.utcnow().isoformat()
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ==================== Statistics ====================

@bp.route('/stats', methods=['GET'])
@jwt_required()
def get_filter_stats():
    """Get overall filtering statistics"""
    try:
        stats = dns_manager.get_filter_stats()
        return jsonify(stats), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/stats/domain/<domain>', methods=['GET'])
@jwt_required()
def get_domain_stats(domain):
    """Get statistics for a specific domain"""
    try:
        stat = DNSDomainStat.query.filter(
            func.lower(DNSDomainStat.domain) == domain.lower()
        ).first()
        
        if not stat:
            return jsonify({'error': 'Domain not found in statistics'}), 404
        
        return jsonify(stat.to_dict()), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/stats/top-domains', methods=['GET'])
@jwt_required()
def get_top_domains():
    """Get top blocked domains"""
    try:
        limit = request.args.get('limit', 10, type=int)
        
        results = db.session.query(
            DNSDomainStat.domain,
            DNSDomainStat.blocked_count,
            DNSDomainStat.category
        ).filter(
            DNSDomainStat.blocked_count > 0
        ).order_by(
            desc(DNSDomainStat.blocked_count)
        ).limit(limit).all()
        
        domains = [
            {
                'domain': r[0],
                'blocked_count': r[1],
                'category': r[2]
            }
            for r in results
        ]
        
        return jsonify({'domains': domains}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/stats/top-clients', methods=['GET'])
@jwt_required()
def get_top_clients():
    """Get top DNS clients"""
    try:
        limit = request.args.get('limit', 10, type=int)
        
        results = db.session.query(
            DNSQueryLog.client_ip,
            DNSQueryLog.client_hostname,
            func.count(DNSQueryLog.id).label('query_count')
        ).filter(
            DNSQueryLog.client_ip.isnot(None)
        ).group_by(
            DNSQueryLog.client_ip,
            DNSQueryLog.client_hostname
        ).order_by(
            desc(func.count(DNSQueryLog.id))
        ).limit(limit).all()
        
        clients = [
            {
                'client_ip': r[0],
                'client_hostname': r[1],
                'query_count': r[2]
            }
            for r in results
        ]
        
        return jsonify({'clients': clients}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/stats/timeline', methods=['GET'])
@jwt_required()
def get_stats_timeline():
    """Get blocking statistics over time"""
    try:
        hours_back = request.args.get('hours', 24, type=int)
        interval_minutes = request.args.get('interval', 60, type=int)
        
        cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
        
        # Group by time intervals
        from sqlalchemy import func as sqla_func
        results = db.session.query(
            sqla_func.datetime(
                sqla_func.strftime('%Y-%m-%d %H:', DNSQueryLog.timestamp),
                'M * ' + str(interval_minutes) + ' minutes'
            ).label('time_bucket'),
            func.count(DNSQueryLog.id).label('total_queries'),
            func.sum(func.cast(DNSQueryLog.was_blocked, db.Integer)).label('blocked_queries')
        ).filter(
            DNSQueryLog.timestamp >= cutoff_time
        ).group_by(
            'time_bucket'
        ).order_by(
            'time_bucket'
        ).all()
        
        timeline = [
            {
                'time': r[0],
                'total_queries': r[1],
                'blocked_queries': r[2] or 0,
                'allowed_queries': (r[1] - (r[2] or 0))
            }
            for r in results
        ]
        
        return jsonify({'timeline': timeline}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ==================== Testing ====================

@bp.route('/test-filter/<domain>', methods=['GET'])
@jwt_required()
def test_filter(domain):
    """Test if a domain would be blocked"""
    try:
        is_blocked, matched_filter = dns_manager.match_domain_against_filters(domain)
        
        return jsonify({
            'domain': domain,
            'would_be_blocked': is_blocked,
            'matched_filter': matched_filter.to_dict() if matched_filter else None
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/config/apply', methods=['POST'])
@jwt_required()
def apply_filter_config():
    """Apply all filter configurations to dnsmasq"""
    try:
        dns_manager.create_dnsmasq_filter_config()
        dns_manager.apply_blocklist_to_dnsmasq()
        dns_manager.apply_allowlist_to_dnsmasq()
        
        # Try to restart but don't fail if it doesn't work
        restart_status = 'success'
        try:
            dns_manager.restart_dnsmasq()
        except Exception as restart_error:
            from flask import current_app
            current_app.logger.warning(f'Config applied but could not restart dnsmasq: {str(restart_error)}')
            restart_status = 'warning'
        
        return jsonify({
            'message': 'DNS filter configuration applied successfully',
            'restart_status': restart_status,
            'note': 'Filter rules are saved. If dnsmasq restart failed, manual restart may be needed.'
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/dashboard/summary', methods=['GET'])
@jwt_required()
def get_dashboard_summary():
    """Get comprehensive dashboard summary with real-time statistics"""
    try:
        from sqlalchemy import func
        from datetime import datetime, timedelta
        
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Get today's statistics
        total_queries_today = DNSQueryLog.query.filter(
            DNSQueryLog.timestamp >= today_start
        ).count()
        
        blocked_today = DNSQueryLog.query.filter(
            (DNSQueryLog.was_blocked == True) &
            (DNSQueryLog.timestamp >= today_start)
        ).count()
        
        allowed_today = total_queries_today - blocked_today
        
        block_rate = round((blocked_today / total_queries_today * 100), 2) if total_queries_today > 0 else 0
        
        # Get filter counts
        active_filters = DomainFilter.query.filter(
            (DomainFilter.enabled == True) &
            (DomainFilter.blocking_enabled == True)
        ).count()
        
        total_filters = DomainFilter.query.count()
        
        blocklists = DomainFilterGroup.query.filter(
            (DomainFilterGroup.enabled == True) &
            (DomainFilterGroup.list_type == 'blocklist')
        ).count()
        
        allowlists = DomainFilterGroup.query.filter(
            (DomainFilterGroup.enabled == True) &
            (DomainFilterGroup.list_type == 'allowlist')
        ).count()
        
        # Get top blocked domains
        top_blocked = db.session.query(
            DNSQueryLog.query_domain,
            func.count(DNSQueryLog.id).label('count')
        ).filter(
            (DNSQueryLog.was_blocked == True) &
            (DNSQueryLog.timestamp >= today_start)
        ).group_by(
            DNSQueryLog.query_domain
        ).order_by(
            func.count(DNSQueryLog.id).desc()
        ).limit(10).all()
        
        # Get top clients
        top_clients = db.session.query(
            DNSQueryLog.client_ip,
            func.count(DNSQueryLog.id).label('count')
        ).filter(
            DNSQueryLog.timestamp >= today_start
        ).group_by(
            DNSQueryLog.client_ip
        ).order_by(
            func.count(DNSQueryLog.id).desc()
        ).limit(10).all()
        
        # Get timeline data (hourly)
        timeline_data = []
        for i in range(24):
            hour_start = today_start + timedelta(hours=i)
            hour_end = hour_start + timedelta(hours=1)
            
            hour_queries = DNSQueryLog.query.filter(
                (DNSQueryLog.timestamp >= hour_start) &
                (DNSQueryLog.timestamp < hour_end)
            ).count()
            
            hour_blocked = DNSQueryLog.query.filter(
                (DNSQueryLog.was_blocked == True) &
                (DNSQueryLog.timestamp >= hour_start) &
                (DNSQueryLog.timestamp < hour_end)
            ).count()
            
            timeline_data.append({
                'hour': i,
                'time': hour_start.strftime('%H:00'),
                'queries': hour_queries,
                'blocked': hour_blocked
            })
        
        return jsonify({
            'summary': {
                'queries_today': total_queries_today,
                'blocked_today': blocked_today,
                'allowed_today': allowed_today,
                'block_rate': block_rate,
                'active_filters': active_filters,
                'total_filters': total_filters,
                'blocklists': blocklists,
                'allowlists': allowlists
            },
            'top_blocked_domains': [
                {'domain': d[0], 'count': d[1]}
                for d in top_blocked
            ],
            'top_clients': [
                {'client_ip': c[0], 'count': c[1]}
                for c in top_clients
            ],
            'timeline': timeline_data
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting dashboard summary: {str(e)}")
        return jsonify({'error': str(e)}), 500