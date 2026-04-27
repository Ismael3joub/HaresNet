
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required
from app import db
from app.models import RouterConfig
from app.services.network_interface_manager import NetworkInterfaceManager

bp = Blueprint('router', __name__)
net_manager = NetworkInterfaceManager()

@bp.route('/wan', methods=['GET'])
@jwt_required()
def get_wan_config():
    """Get current WAN configuration"""
    config = RouterConfig.query.first()
    
    if not config:
        # Return default structure
        return jsonify({
            'mode': 'dhcp',
            'static_ip': '',
            'gateway': '',
            'subnet_mask': '255.255.255.0',
            'dns_primary': '8.8.8.8',
            'dns_secondary': '8.8.4.4'
        }), 200
        
    return jsonify(config.to_dict()['wan']), 200

@bp.route('/wan', methods=['PUT'])
@jwt_required()
def update_wan_config():
    """Update WAN configuration"""
    data = request.get_json()
    
    # Validation
    if data.get('mode') not in ['dhcp', 'static']:
        return jsonify({'error': 'Invalid mode (must be dhcp or static)'}), 400
        
    if data.get('mode') == 'static':
        if not data.get('static_ip'):
            return jsonify({'error': 'Static IP is required for static mode'}), 400
        if not data.get('gateway'):
            return jsonify({'error': 'Gateway is required for static mode'}), 400
            
    try:
        config = RouterConfig.query.first()
        if not config:
            config = RouterConfig()
            db.session.add(config)
            
        # Update model
        config.wan_mode = data.get('mode')
        config.wan_static_ip = data.get('static_ip')
        config.wan_gateway = data.get('gateway')
        config.wan_subnet_mask = data.get('subnet_mask', '255.255.255.0')
        config.wan_dns_primary = data.get('dns_primary')
        config.wan_dns_secondary = data.get('dns_secondary')
        
        db.session.commit()
        
        # Apply configuration
        success, message = net_manager.apply_wan_config(config)
        
        if success:
            return jsonify({
                'message': 'WAN configuration updated successfully',
                'details': message
            }), 200
        else:
            return jsonify({
                'error': 'Configuration saved but failed to apply',
                'details': message
            }), 500
            
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/lan', methods=['GET'])
@jwt_required()
def get_lan_config():
    """Get current LAN configuration"""
    config = RouterConfig.query.first()
    
    if not config:
        return jsonify({
            'ip': '192.168.10.1',
            'subnet_mask': '255.255.255.0',
            'dhcp_enabled': True,
            'dhcp_start': '192.168.10.100',
            'dhcp_end': '192.168.10.200'
        }), 200
        
    return jsonify(config.to_dict()['lan']), 200

@bp.route('/lan', methods=['PUT'])
@jwt_required()
def update_lan_config():
    """Update LAN configuration"""
    data = request.get_json()
    
    # Validation
    if not data.get('ip'):
        return jsonify({'error': 'LAN IP is required'}), 400
        
    try:
        config = RouterConfig.query.first()
        if not config:
            config = RouterConfig()
            db.session.add(config)
            
        # Update model
        config.lan_ip = data.get('ip')
        config.lan_subnet_mask = data.get('subnet_mask', '255.255.255.0')
        config.lan_dhcp_enabled = data.get('dhcp_enabled', True)
        config.lan_dhcp_start = data.get('dhcp_start')
        config.lan_dhcp_end = data.get('dhcp_end')
        
        db.session.commit()
        
        # Note: Applying LAN config might disconnect clients
        # We should restart dnsmasq to update DHCP range as well
        
        success, message = net_manager.apply_lan_config(config)
        
        # Restart dnsmasq to apply DHCP changes
        from app.services.dnsmasq_manager import DnsmasqManager
        import subprocess
        
        dnsmasq = DnsmasqManager()
        dnsmasq.generate_config()
        
        # Restart dnsmasq (container-safe method)
        try:
            subprocess.run(['pkill', 'dnsmasq'], check=False)
            subprocess.run(['dnsmasq'], check=True)
        except Exception as e:
            current_app.logger.warning(f"Failed to restart dnsmasq: {e}")
        
        if success:
            return jsonify({
                'message': 'LAN configuration updated successfully',
                'details': message
            }), 200
        else:
            return jsonify({
                'error': 'Configuration saved but failed to apply',
                'details': message
            }), 500
            
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
