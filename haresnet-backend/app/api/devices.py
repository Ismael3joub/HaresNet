from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app import db
from app.models import Device
from app.services.nftables_manager import NftablesManager
from app.services.hostapd_manager import HostapdManager
from datetime import datetime

bp = Blueprint('devices', __name__)
nft_manager = NftablesManager()
hostapd_manager = HostapdManager()

@bp.route('', methods=['GET'])
@jwt_required()
def get_devices():
    """Get all devices"""
    group = request.args.get('group')
    blocked = request.args.get('blocked')
    
    query = Device.query
    
    if group:
        query = query.filter_by(group=group)
    
    if blocked is not None:
        blocked_bool = blocked.lower() == 'true'
        query = query.filter_by(blocked=blocked_bool)
    
    devices = query.order_by(Device.last_seen.desc()).all()
    
    return jsonify({
        'devices': [device.to_dict() for device in devices],
        'total': len(devices)
    }), 200

@bp.route('/<int:device_id>', methods=['GET'])
@jwt_required()
def get_device(device_id):
    """Get device details"""
    device = Device.query.get(device_id)
    
    if not device:
        return jsonify({'error': 'Device not found'}), 404
    
    return jsonify(device.to_dict()), 200

@bp.route('/<int:device_id>', methods=['PUT'])
@jwt_required()
def update_device(device_id):
    """Update device label, group, etc."""
    device = Device.query.get(device_id)
    
    if not device:
        return jsonify({'error': 'Device not found'}), 404
    
    data = request.get_json()
    
    if 'label' in data:
        device.label = data['label']
    
    if 'group' in data:
        device.group = data['group']
    
    if 'group' in data:
        device.group = data['group']
        
    if 'traffic_limit_daily_mb' in data:
        device.traffic_limit_daily_mb = int(data['traffic_limit_daily_mb'])
        
    if 'traffic_limit_hourly_mb' in data:
        device.traffic_limit_hourly_mb = int(data['traffic_limit_hourly_mb'])

    if 'child_safe' in data:
        device.child_safe = data['child_safe']
        from app import socketio
        from flask import current_app
        app_instance = current_app._get_current_object()
        
        # Clear conntrack IMMEDIATELY for this device to force DNS re-lookup
        # Clear conntrack and DISCONNECT client to force DNS flush
        if device.ip:
            try:
                from app.services.nftables_manager import NftablesManager
                from app.services.hostapd_manager import HostapdManager
                
                # 1. Clear conntrack
                nft_mgr = NftablesManager()
                nft_mgr.clear_conntrack(device.ip)
                print(f"[CHILD-MODE-TOGGLE] Cleared conntrack for {device.label} ({device.ip})", flush=True)
                
                # 2. Force Disconnect (triggers DNS flush on client)
                if device.mac:
                    hostapd = HostapdManager()
                    hostapd.disconnect_device(device.mac)
                    print(f"[CHILD-MODE-TOGGLE] Disconnected {device.label} ({device.mac}) to force DNS flush", flush=True)
                    
            except Exception as e:
                print(f"[CHILD-MODE-TOGGLE] Failed to enforce: {e}", flush=True)
        
        def apply_rules_task():
            try:
                with app_instance.app_context():
                    # Re-instantiate manager within context to ensure it has app config
                    from app.services.nftables_manager import NftablesManager
                    NftablesManager().apply_child_safety_rules()
            except Exception as e:
                app_instance.logger.error(f"Failed to apply child safety rules in background: {e}")
        
        socketio.start_background_task(apply_rules_task)
    
    db.session.commit()

    # Emit socket event
    from app import socketio
    socketio.emit('device_update', {'id': device.id, 'action': 'update'})
    
    return jsonify({
        'message': 'Device updated successfully',
        'device': device.to_dict()
    }), 200

@bp.route('/<int:device_id>/block', methods=['POST'])
@jwt_required()
def block_device(device_id):
    """Block device access"""
    device = Device.query.get(device_id)
    
    if not device:
        return jsonify({'error': 'Device not found'}), 404
    
    if not device.mac:
        return jsonify({'error': 'Device has no MAC address'}), 400
    
    device.blocked = True
    db.session.commit()
    
    # Apply firewall rules
    try:
        # Apply device rules to nftables
        nft_manager.apply_device_rules()
        
        # Also add a direct rule for this specific device as backup
        nft_manager.apply_schedule_rule(device.mac, 'block')
        
        # Update hostapd deny list
        blocked_devices = Device.query.filter_by(blocked=True).all()
        blocked_macs = [d.mac for d in blocked_devices if d.mac]
        hostapd_manager.update_deny_list(blocked_macs)

        # Emit socket event
        from app import socketio
        socketio.emit('device_update', {'id': device.id, 'action': 'block', 'blocked': True})
            
        return jsonify({
            'message': 'Device blocked successfully',
            'device': device.to_dict()
        }), 200
    except Exception as e:
        return jsonify({'error': f'Failed to apply firewall rule: {str(e)}'}), 500

@bp.route('/<int:device_id>/unblock', methods=['POST'])
@jwt_required()
def unblock_device(device_id):
    """Unblock device access"""
    device = Device.query.get(device_id)
    
    if not device:
        return jsonify({'error': 'Device not found'}), 404
    
    if not device.mac:
        return jsonify({'error': 'Device has no MAC address'}), 400
    
    device.blocked = False
    db.session.commit()
    
    # Remove firewall rules
    try:
        # Reapply device rules to remove this device
        nft_manager.apply_device_rules()
        
        # Also remove direct rule for this specific device
        nft_manager.apply_schedule_rule(device.mac, 'allow')
        
        # Update hostapd deny list (will remove the unblocked device)
        blocked_devices = Device.query.filter_by(blocked=True).all()
        blocked_macs = [d.mac for d in blocked_devices if d.mac]
        hostapd_manager.update_deny_list(blocked_macs)

        # Emit socket event
        from app import socketio
        socketio.emit('device_update', {'id': device.id, 'action': 'unblock', 'blocked': False})
            
        return jsonify({
            'message': 'Device unblocked successfully',
            'device': device.to_dict()
        }), 200
    except Exception as e:
        return jsonify({'error': f'Failed to apply firewall rule: {str(e)}'}), 500

@bp.route('/<int:device_id>', methods=['DELETE'])
@jwt_required()
def delete_device(device_id):
    """Forget device (remove from database)"""
    device = Device.query.get(device_id)
    
    if not device:
        return jsonify({'error': 'Device not found'}), 404
    
    db.session.delete(device)
    db.session.commit()
    
    return jsonify({'message': 'Device removed successfully'}), 200

@bp.route('/groups', methods=['GET'])
@jwt_required()
def get_groups():
    """Get all unique device groups"""
    groups = db.session.query(Device.group).distinct().filter(Device.group.isnot(None)).all()
    
    return jsonify({
        'groups': [g[0] for g in groups]
    }), 200

@bp.route('/<int:device_id>/traffic', methods=['GET'])
@jwt_required()
def get_device_traffic(device_id):
    """Get device traffic history with flexible time range options"""
    from app.models import DeviceTraffic
    from datetime import datetime, timedelta
    
    # Check if device exists
    device = Device.query.get(device_id)
    if not device:
        return jsonify({'error': 'Device not found'}), 404
    
    # Get query parameters
    hours = request.args.get('hours', type=int)
    since_str = request.args.get('since')
    until_str = request.args.get('until')
    aggregate_window = request.args.get('aggregate')  # e.g., "1m", "5m", "1h", "1d"
    
    # Determine time range
    if since_str and until_str:
        try:
            since = datetime.fromisoformat(since_str.replace('Z', '+00:00'))
            until = datetime.fromisoformat(until_str.replace('Z', '+00:00'))
        except ValueError:
            return jsonify({'error': 'Invalid date format. Use ISO 8601 format'}), 400
    elif hours:
        since = datetime.utcnow() - timedelta(hours=hours)
        until = datetime.utcnow()
    else:
        # Default to last 24 hours
        since = datetime.utcnow() - timedelta(hours=24)
        until = datetime.utcnow()
    
    # Try to query from InfluxDB first (better performance for time-series)
    traffic_data = []
    data_source = 'sqlite'  # Track which source we used
    
    try:
        from app.services.influxdb_service import InfluxDBService
        influxdb = InfluxDBService()
        
        if influxdb.is_connected():
            traffic_data = influxdb.query_device_traffic(
                device_id=device_id,
                start_time=since,
                end_time=until,
                aggregate_window=aggregate_window
            )
            data_source = 'influxdb'
    except Exception as e:
        print(f"[API] InfluxDB query failed: {str(e)}", flush=True)
    
    # Fallback to SQLite if InfluxDB failed or returned no data
    if not traffic_data:
        traffic = DeviceTraffic.query.filter(
            DeviceTraffic.device_id == device_id,
            DeviceTraffic.timestamp >= since,
            DeviceTraffic.timestamp <= until
        ).order_by(DeviceTraffic.timestamp.asc()).all()
        
        traffic_data = [{
            'timestamp': t.timestamp.isoformat(),
            'upload': t.bytes_sent,
            'download': t.bytes_received
        } for t in traffic]
    
    # Calculate totals
    total_upload = sum(t['upload'] for t in traffic_data)
    total_download = sum(t['download'] for t in traffic_data)
    
    # Format bytes
    def format_bytes(bytes_val):
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_val < 1024.0:
                return f"{bytes_val:.2f} {unit}"
            bytes_val /= 1024.0
        return f"{bytes_val:.2f} PB"
    
    return jsonify({
        'device_id': device_id,
        'device': {
            'mac': device.mac,
            'hostname': device.hostname,
            'ip': device.ip,
            'label': device.label
        },
        'time_range': {
            'since': since.isoformat(),
            'until': until.isoformat()
        },
        'summary': {
            'total_upload': total_upload,
            'total_download': total_download,
            'total_upload_formatted': format_bytes(total_upload),
            'total_download_formatted': format_bytes(total_download),
            'data_points': len(traffic_data)
        },
        'traffic': traffic_data,
        'data_source': data_source  # Indicate which database was used
    }), 200

@bp.route('/traffic/rates', methods=['GET'])
@jwt_required()
def get_traffic_rates():
    """Get current traffic rates for all devices"""
    from app.services.traffic_monitor import TrafficMonitor
    
    traffic_monitor = TrafficMonitor()
    rates = traffic_monitor.get_current_rates()
    
    return jsonify({
        'rates': list(rates.values()),
        'timestamp': datetime.utcnow().isoformat()
    }), 200

@bp.route('/traffic/network', methods=['GET'])
@jwt_required()
def get_network_traffic():
    """Get network-wide traffic statistics (all devices combined)"""
    from datetime import datetime, timedelta
    
    # Get query parameters
    hours = request.args.get('hours', type=int, default=24)
    aggregate_window = request.args.get('aggregate', default='5m')  # Default 5-minute aggregation
    
    since = datetime.utcnow() - timedelta(hours=hours)
    until = datetime.utcnow()
    
    # Try InfluxDB first
    try:
        from app.services.influxdb_service import InfluxDBService
        influxdb = InfluxDBService()
        
        if influxdb.is_connected():
            traffic_data = influxdb.query_network_traffic(
                start_time=since,
                end_time=until,
                aggregate_window=aggregate_window
            )
            
            # Calculate totals
            total_upload = sum(t['upload'] for t in traffic_data)
            total_download = sum(t['download'] for t in traffic_data)
            
            def format_bytes(bytes_val):
                for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
                    if bytes_val < 1024.0:
                        return f"{bytes_val:.2f} {unit}"
                    bytes_val /= 1024.0
                return f"{bytes_val:.2f} PB"
            
            return jsonify({
                'time_range': {
                    'since': since.isoformat(),
                    'until': until.isoformat(),
                    'hours': hours
                },
                'aggregation': aggregate_window,
                'summary': {
                    'total_upload': total_upload,
                    'total_download': total_download,
                    'total_upload_formatted': format_bytes(total_upload),
                    'total_download_formatted': format_bytes(total_download),
                    'total_traffic': total_upload + total_download,
                    'total_traffic_formatted': format_bytes(total_upload + total_download),
                    'data_points': len(traffic_data)
                },
                'traffic': traffic_data
            }), 200
    except Exception as e:
        print(f"[API] InfluxDB network query failed: {str(e)}", flush=True)
    
    # Fallback to SQLite aggregation
    from app.models import DeviceTraffic
    traffic = DeviceTraffic.query.filter(
        DeviceTraffic.timestamp >= since,
        DeviceTraffic.timestamp <= until
    ).order_by(DeviceTraffic.timestamp.asc()).all()
    
    total_upload = sum(t.bytes_sent for t in traffic)
    total_download = sum(t.bytes_received for t in traffic)
    
    # Aggregate into time buckets for chart display
    # Parse aggregate_window (e.g. "1m", "5m", "15m", "1h")
    bucket_seconds = 300  # default 5 minutes
    if aggregate_window:
        try:
            if aggregate_window.endswith('m'):
                bucket_seconds = int(aggregate_window[:-1]) * 60
            elif aggregate_window.endswith('h'):
                bucket_seconds = int(aggregate_window[:-1]) * 3600
            elif aggregate_window.endswith('d'):
                bucket_seconds = int(aggregate_window[:-1]) * 86400
        except (ValueError, IndexError):
            bucket_seconds = 300
    
    buckets = {}
    for t in traffic:
        # Round timestamp down to nearest bucket
        ts_epoch = int(t.timestamp.timestamp())
        bucket_epoch = (ts_epoch // bucket_seconds) * bucket_seconds
        bucket_key = datetime.utcfromtimestamp(bucket_epoch)
        
        if bucket_key not in buckets:
            buckets[bucket_key] = {'upload': 0, 'download': 0}
        buckets[bucket_key]['upload'] += t.bytes_sent
        buckets[bucket_key]['download'] += t.bytes_received
    
    traffic_data = [
        {
            'timestamp': ts.isoformat(),
            'upload': data['upload'],
            'download': data['download']
        }
        for ts, data in sorted(buckets.items())
    ]
    
    def format_bytes(bytes_val):
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_val < 1024.0:
                return f"{bytes_val:.2f} {unit}"
            bytes_val /= 1024.0
        return f"{bytes_val:.2f} PB"
    
    return jsonify({
        'time_range': {
            'since': since.isoformat(),
            'until': until.isoformat(),
            'hours': hours
        },
        'aggregation': aggregate_window,
        'summary': {
            'total_upload': total_upload,
            'total_download': total_download,
            'total_upload_formatted': format_bytes(total_upload),
            'total_download_formatted': format_bytes(total_download),
            'total_traffic': total_upload + total_download,
            'total_traffic_formatted': format_bytes(total_upload + total_download),
            'data_points': len(traffic_data)
        },
        'traffic': traffic_data,
        'data_source': 'sqlite'
    }), 200

@bp.route('/traffic/top', methods=['GET'])
@jwt_required()
def get_top_devices():
    """Get top devices by traffic usage"""
    # Get query parameters
    limit = request.args.get('limit', type=int, default=10)
    hours = request.args.get('hours', type=int, default=24)
    sort_by = request.args.get('sort_by', default='total')  # 'total', 'upload', or 'download'
    
    # Try InfluxDB first
    try:
        from app.services.influxdb_service import InfluxDBService
        influxdb = InfluxDBService()
        
        if influxdb.is_connected():
            top_devices = influxdb.get_top_devices(
                limit=limit,
                hours=hours,
                sort_by=sort_by
            )
            
            def format_bytes(bytes_val):
                for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
                    if bytes_val < 1024.0:
                        return f"{bytes_val:.2f} {unit}"
                    bytes_val /= 1024.0
                return f"{bytes_val:.2f} PB"
            
            # Add formatted values
            for device in top_devices:
                device['upload_formatted'] = format_bytes(device['upload'])
                device['download_formatted'] = format_bytes(device['download'])
                device['total_formatted'] = format_bytes(device['total'])
            
            return jsonify({
                'top_devices': top_devices,
                'limit': limit,
                'hours': hours,
                'sort_by': sort_by
            }), 200
    except Exception as e:
        print(f"[API] InfluxDB top devices query failed: {str(e)}", flush=True)
    
    # Fallback to SQLite
    from app.models import DeviceTraffic
    from datetime import datetime, timedelta
    from sqlalchemy import func
    
    since = datetime.utcnow() - timedelta(hours=hours)
    
    # Group by device and sum traffic
    device_stats = db.session.query(
        DeviceTraffic.device_id,
        func.sum(DeviceTraffic.bytes_sent).label('upload'),
        func.sum(DeviceTraffic.bytes_received).label('download')
    ).filter(
        DeviceTraffic.timestamp >= since
    ).group_by(DeviceTraffic.device_id).all()
    
    # Format results
    devices = []
    for stat in device_stats:
        device = Device.query.get(stat.device_id)
        if device:
            upload = int(stat.upload or 0)
            download = int(stat.download or 0)
            total = upload + download
            
            devices.append({
                'device_id': device.id,
                'mac': device.mac,
                'hostname': device.hostname,
                'upload': upload,
                'download': download,
                'total': total
            })
    
    # Sort
    if sort_by == 'upload':
        devices.sort(key=lambda x: x['upload'], reverse=True)
    elif sort_by == 'download':
        devices.sort(key=lambda x: x['download'], reverse=True)
    else:
        devices.sort(key=lambda x: x['total'], reverse=True)
    
    # Limit and format
    def format_bytes(bytes_val):
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_val < 1024.0:
                return f"{bytes_val:.2f} {unit}"
            bytes_val /= 1024.0
        return f"{bytes_val:.2f} PB"
    
    top_devices = devices[:limit]
    for device in top_devices:
        device['upload_formatted'] = format_bytes(device['upload'])
        device['download_formatted'] = format_bytes(device['download'])
        device['total_formatted'] = format_bytes(device['total'])
    
    return jsonify({
        'top_devices': top_devices,
        'limit': limit,
        'hours': hours,
        'sort_by': sort_by,
        'data_source': 'sqlite'
    }), 200
