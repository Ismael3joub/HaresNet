from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app import db
from app.models import SystemSettings
import os
import zoneinfo

bp = Blueprint('settings', __name__)

# Common timezones list
COMMON_TIMEZONES = [
    "Africa/Cairo",
    "Africa/Johannesburg",
    "America/New_York",
    "America/Chicago",
    "America/Denver",
    "America/Los_Angeles",
    "America/Toronto",
    "America/Mexico_City",
    "America/Sao_Paulo",
    "America/Argentina/Buenos_Aires",
    "Europe/London",
    "Europe/Paris",
    "Europe/Berlin",
    "Europe/Rome",
    "Europe/Madrid",
    "Europe/Amsterdam",
    "Europe/Brussels",
    "Europe/Vienna",
    "Europe/Stockholm",
    "Europe/Moscow",
    "Europe/Istanbul",
    "Asia/Dubai",
    "Asia/Kolkata",
    "Asia/Bangkok",
    "Asia/Singapore",
    "Asia/Hong_Kong",
    "Asia/Shanghai",
    "Asia/Tokyo",
    "Asia/Seoul",
    "Australia/Sydney",
    "Australia/Melbourne",
    "Pacific/Auckland",
    "UTC",
]

@bp.route('/timezones', methods=['GET'])
@jwt_required()
def get_timezones():
    """Get list of available timezones"""
    return jsonify({
        'timezones': COMMON_TIMEZONES
    }), 200

@bp.route('', methods=['GET'])
@jwt_required()
def get_settings():
    """Get system settings"""
    # Get timezone setting
    tz_setting = SystemSettings.query.filter_by(key='timezone').first()
    
    if not tz_setting:
        # Initialize with environment or default
        default_tz = os.environ.get('TIMEZONE', 'UTC')
        tz_setting = SystemSettings(key='timezone', value=default_tz)
        db.session.add(tz_setting)
        db.session.commit()
    
    # Get NTFY Topic
    ntfy_setting = SystemSettings.query.filter_by(key='ntfy_topic').first()
    if not ntfy_setting:
        default_topic = os.environ.get('NTFY_TOPIC', 'haresnet_admin')
        ntfy_setting = SystemSettings(key='ntfy_topic', value=default_topic)
        db.session.add(ntfy_setting)
        db.session.commit()

    # Get Admin Email
    email_setting = SystemSettings.query.filter_by(key='admin_email').first()
    if not email_setting:
        email_setting = SystemSettings(key='admin_email', value='')
        db.session.add(email_setting)
        db.session.commit()

    # Get 2FA Enabled
    two_factor_setting = SystemSettings.query.filter_by(key='two_factor_enabled').first()
    if not two_factor_setting:
        # Default to False
        two_factor_setting = SystemSettings(key='two_factor_enabled', value='false')
        db.session.add(two_factor_setting)
        db.session.commit()
    
    return jsonify({
        'timezone': tz_setting.value,
        'ntfy_topic': ntfy_setting.value,
        'admin_email': email_setting.value,
        'two_factor_enabled': two_factor_setting.value.lower() == 'true',
        'two_factor_enabled': two_factor_setting.value.lower() == 'true',
        'updated_at': tz_setting.updated_at.isoformat()
    }), 200



@bp.route('', methods=['PUT'])
@jwt_required()
def update_settings():
    """Update system settings"""
    data = request.get_json()
    
    response_data = {'message': 'Settings updated successfully'}
    updated = False

    if 'timezone' in data:
        # Validate timezone
        try:
            zoneinfo.ZoneInfo(data['timezone'])
        except Exception:
            return jsonify({'error': 'Invalid timezone'}), 400
        
        tz_setting = SystemSettings.query.filter_by(key='timezone').first()
        
        if not tz_setting:
            tz_setting = SystemSettings(key='timezone', value=data['timezone'])
            db.session.add(tz_setting)
        else:
            tz_setting.value = data['timezone']
        
        response_data['timezone'] = tz_setting.value
        updated = True

    if 'ntfy_topic' in data:
        topic = data['ntfy_topic'].strip()
        if not topic:
            return jsonify({'error': 'Topc cannot be empty'}), 400
            
        ntfy_setting = SystemSettings.query.filter_by(key='ntfy_topic').first()
        if not ntfy_setting:
            ntfy_setting = SystemSettings(key='ntfy_topic', value=topic)
            db.session.add(ntfy_setting)
        else:
            ntfy_setting.value = topic
        
        response_data['ntfy_topic'] = ntfy_setting.value
        updated = True

    if 'admin_email' in data:
        email = data['admin_email'].strip()
        # Basic validation could go here
        
        email_setting = SystemSettings.query.filter_by(key='admin_email').first()
        if not email_setting:
            email_setting = SystemSettings(key='admin_email', value=email)
            db.session.add(email_setting)
        else:
            email_setting.value = email
        
        response_data['admin_email'] = email_setting.value
        updated = True
        
    if 'two_factor_enabled' in data:
        enabled = str(data['two_factor_enabled']).lower()
        
        two_factor_setting = SystemSettings.query.filter_by(key='two_factor_enabled').first()
        if not two_factor_setting:
            two_factor_setting = SystemSettings(key='two_factor_enabled', value=enabled)
            db.session.add(two_factor_setting)
        else:
            two_factor_setting.value = enabled
            
        response_data['two_factor_enabled'] = two_factor_setting.value.lower() == 'true'
        updated = True

    if updated:
        db.session.commit()
        return jsonify(response_data), 200
    
    return jsonify({'error': 'No settings provided'}), 400
