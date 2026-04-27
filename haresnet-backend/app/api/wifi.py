from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required
from app import db
from app.models import WiFiConfig, SystemSettings
from app.services.hostapd_manager import HostapdManager

bp = Blueprint('wifi', __name__)
hostapd_manager = HostapdManager()

@bp.route('/config', methods=['GET'])
@jwt_required()
def get_config():
    """Get current Wi-Fi configuration (router-only)"""
    # Get router WiFi configuration from WiFiConfig model
    config = WiFiConfig.query.first()
    
    if not config:
        # Create default config if none exists
        config = WiFiConfig(
            ssid='HaresNet',
            password='haresnet2024',
            security_mode='WPA2',
            band='2.4GHz',
            channel=6,
            hidden=False
        )
        db.session.add(config)
        db.session.commit()
    
    return jsonify(config.to_dict()), 200

@bp.route('/config', methods=['PUT'])
@jwt_required()
def update_config():
    """Update Wi-Fi configuration (router-only)"""
    data = request.get_json()
    
    # Validate parameters
    if 'ssid' in data:
        if not data['ssid'] or len(data['ssid']) > 32:
            return jsonify({'error': 'SSID must be 1-32 characters'}), 400
    
    if 'security_mode' in data:
        if data['security_mode'] not in ['WPA2', 'WPA3', 'WPA2/WPA3', 'OPEN', 'WEP']:
            return jsonify({'error': 'Invalid security mode'}), 400
    
    if 'password' in data and data.get('security_mode') != 'OPEN':
        if len(data['password']) < 8 or len(data['password']) > 63:
            return jsonify({'error': 'Password must be 8-63 characters'}), 400
    
    if 'channel' in data:
        if not (1 <= data['channel'] <= 13):
            return jsonify({'error': 'Channel must be between 1 and 13'}), 400
    
    try:
        # Update router WiFi configuration in WiFiConfig model
        config = WiFiConfig.query.first()
        
        if not config:
            config = WiFiConfig(band='2.4GHz')
            db.session.add(config)
        
        if 'ssid' in data:
            config.ssid = data['ssid']
        if 'password' in data:
            config.password = data['password']
        if 'security_mode' in data:
            config.security_mode = data['security_mode']
        if 'channel' in data:
            config.channel = data['channel']
        if 'hidden' in data:
            config.hidden = data['hidden']
        if 'band' in data:
            # Force 2.4GHz for router-only mode
            config.band = '2.4GHz'
        
        db.session.commit()
        
        # Generate new hostapd configuration
        hostapd_manager.generate_config(config)
        return jsonify({
            'message': 'Wi-Fi configuration updated successfully',
            'config': config.to_dict(),
            'note': 'Restart the AP to apply changes'
        }), 200
    except Exception as e:
        return jsonify({'error': f'Failed to update configuration: {str(e)}'}), 500

def _update_setting(key, value):
    """Helper function to update SystemSettings"""
    setting = SystemSettings.query.filter_by(key=key).first()
    if not setting:
        setting = SystemSettings(key=key, value=value)
        db.session.add(setting)
    else:
        setting.value = value
    db.session.commit()

@bp.route('/restart', methods=['POST'])
@jwt_required()
def restart_ap():
    """Restart the access point"""
    try:
        hostapd_manager.restart()
        return jsonify({'message': 'Access point restarted successfully'}), 200
    except Exception as e:
        return jsonify({'error': f'Failed to restart AP: {str(e)}'}), 500

@bp.route('/status', methods=['GET'])
@jwt_required()
def get_status():
    """Get AP status"""
    try:
        status = hostapd_manager.get_status()
        return jsonify(status), 200
    except Exception as e:
        return jsonify({'error': f'Failed to get status: {str(e)}'}), 500
