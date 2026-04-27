from flask import Blueprint, jsonify, current_app
from flask_jwt_extended import jwt_required
import psutil
import netifaces
from datetime import datetime

from app.services.system_monitor import monitor

bp = Blueprint('system', __name__)

@bp.route('/status', methods=['GET'])
@jwt_required()
def get_status():
    """Get system status (CPU, RAM, Network)"""
    try:
        stats = monitor.get_stats()
        return jsonify(stats), 200
    except Exception as e:
        return jsonify({'error': f'Failed to get system status: {str(e)}'}), 500

@bp.route('/interfaces', methods=['GET'])
@jwt_required()
def get_interfaces():
    """Get network interfaces"""
    try:
        interfaces = []
        
        for iface in netifaces.interfaces():
            addrs = netifaces.ifaddresses(iface)
            
            ipv4 = None
            if netifaces.AF_INET in addrs:
                ipv4 = addrs[netifaces.AF_INET][0]['addr']
            
            mac = None
            if netifaces.AF_LINK in addrs:
                mac = addrs[netifaces.AF_LINK][0]['addr']
            
            # Get interface stats
            stats = psutil.net_if_stats().get(iface)
            
            interfaces.append({
                'name': iface,
                'ipv4': ipv4,
                'mac': mac,
                'is_up': stats.isup if stats else False,
                'speed': stats.speed if stats else 0
            })
        
        return jsonify({
            'interfaces': interfaces
        }), 200
    except Exception as e:
        return jsonify({'error': f'Failed to get interfaces: {str(e)}'}), 500

@bp.route('/network-stats', methods=['GET'])
@jwt_required()
def get_network_stats():
    """Get network statistics"""
    try:
        net_io = psutil.net_io_counters()
        
        return jsonify({
            'bytes_sent': net_io.bytes_sent,
            'bytes_recv': net_io.bytes_recv,
            'packets_sent': net_io.packets_sent,
            'packets_recv': net_io.packets_recv,
            'errin': net_io.errin,
            'errout': net_io.errout,
            'dropin': net_io.dropin,
            'dropout': net_io.dropout
        }), 200
    except Exception as e:
        return jsonify({'error': f'Failed to get network stats: {str(e)}'}), 500

@bp.route('/speedtest', methods=['POST'])
@jwt_required()
def run_speedtest():
    """Start internet speed test in background"""
    from app import socketio
    
    # Capture app for background task
    app_instance = current_app._get_current_object()
    
    def task_wrapper():
        with app_instance.app_context():
            try:
                monitor.run_speedtest()
            except Exception as e:
                print(f"Speedtest background task failed: {e}")
    
    # Use socketio background task
    socketio.start_background_task(task_wrapper)
    
    return jsonify({
        'status': 'started',
        'message': 'Speed test started in background'
    }), 202
