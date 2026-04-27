from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from app import db
from app.models import User

bp = Blueprint('auth', __name__)

@bp.route('/login', methods=['POST'])
def login():
    """Authenticate user and return JWT token"""
    data = request.get_json()
    
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'error': 'Missing username or password'}), 400
    
    user = User.query.filter_by(username=data['username']).first()
    
    if not user or not user.check_password(data['password']):
        return jsonify({'error': 'Invalid credentials'}), 401
        
    # Check if 2FA is enabled in settings
    from app.models import SystemSettings
    two_factor_setting = SystemSettings.query.filter_by(key='two_factor_enabled').first()
    
    # Default to False if not set
    is_2fa_enabled = two_factor_setting.value.lower() == 'true' if two_factor_setting else False

    if is_2fa_enabled:
        from app.services.email_service import EmailService
        from app.services.ntfy_service import NtfyService
        
        email_service = EmailService()
        ntfy_service = NtfyService()

        # Try 2FA via Email OR NTFY (or both, depending on logic)
        try:
            
            import secrets
            import string
            from datetime import datetime, timedelta

            otp = ''.join(secrets.choice(string.digits) for i in range(6))
            user.otp_code = otp
            user.otp_expires_at = datetime.utcnow() + timedelta(seconds=60)
            db.session.commit()

            user.otp_expires_at = datetime.utcnow() + timedelta(seconds=60)
            db.session.commit()

            # Prioritize Email for 2FA OTP
            email_sent = email_service.send_otp(otp)
            
            if email_sent:
                # Email sent successfully, no need for NTFY
                # Get admin email for masking
                from app.models import SystemSettings
                admin_email_setting = SystemSettings.query.filter_by(key='admin_email').first()
                masked_email = ""
                if admin_email_setting and admin_email_setting.value:
                    email = admin_email_setting.value
                    # Mask email: show first 2 chars, last 2 chars of local part, and first 2 chars + ** + extension
                    if '@' in email:
                        local, domain = email.split('@')
                        if '.' in domain:
                            domain_name, domain_ext = domain.rsplit('.', 1)
                            masked_local = local[:2] + '*' * (len(local) - 2) if len(local) > 2 else local
                            masked_domain = domain_name[:2] + '**' if len(domain_name) > 2 else domain_name
                            masked_email = f"{masked_local}@{masked_domain}.{domain_ext[:2]}**"
                        else:
                            masked_local = local[:2] + '*' * (len(local) - 2) if len(local) > 2 else local
                            masked_email = f"{masked_local}@{domain[:2]}**"
                
                return jsonify({
                    'message': 'OTP sent via Email',
                    '2fa_required': True,
                    'masked_email': masked_email,
                    'temp_token': create_access_token(identity=str(user.id), expires_delta=timedelta(minutes=5), additional_claims={'type': '2fa_temp'})
                }), 200
            else:
                # Email failed or not configured, fallback to NTFY
                print("[Auth] Email send failed, falling back to NTFY", flush=True)
                ntfy_sent = ntfy_service.send_otp(otp)
                
                if ntfy_sent:
                    return jsonify({
                        'message': 'OTP sent via NTFY (email unavailable)',
                        '2fa_required': True,
                        'temp_token': create_access_token(identity=str(user.id), expires_delta=timedelta(minutes=5), additional_claims={'type': '2fa_temp'})
                    }), 200
                else:
                    print("[Auth] Failed to send OTP via both Email and NTFY", flush=True)

        except Exception as e:
            import traceback
            traceback.print_exc()

    # Normal login — Blynk disabled, not configured, or OTP failed
    access_token = create_access_token(identity=str(user.id))
    return jsonify({
        'access_token': access_token,
        'user': user.to_dict()
    }), 200

@bp.route('/verify-2fa', methods=['POST'])
@jwt_required()
def verify_2fa():
    """Verify OTP and return full access token"""
    user_id = get_jwt_identity()
    user = User.query.get(int(user_id))
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
        
    data = request.get_json()
    if not data or not data.get('code'):
        return jsonify({'error': 'Missing OTP code'}), 400
        
    from datetime import datetime
    
    if not user.otp_code or not user.otp_expires_at:
        return jsonify({'error': 'No OTP pending'}), 400
        
    if datetime.utcnow() > user.otp_expires_at:
        return jsonify({'error': 'OTP expired'}), 400
        
    if data['code'] != user.otp_code:
        return jsonify({'error': 'Invalid OTP code'}), 401
        
    # Clear OTP
    user.otp_code = None
    user.otp_expires_at = None
    db.session.commit()
    
    # Issue full token
    access_token = create_access_token(identity=str(user.id))
    
    return jsonify({
        'access_token': access_token,
        'user': user.to_dict()
    }), 200

@bp.route('/status', methods=['GET'])
@jwt_required()
def status():
    """Check authentication status"""
    user_id = get_jwt_identity()
    user = User.query.get(int(user_id))
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify({
        'authenticated': True,
        'user': user.to_dict()
    }), 200

@bp.route('/change-password', methods=['POST'])
@jwt_required()
def change_password():
    """Change user password"""
    user_id = get_jwt_identity()
    user = User.query.get(int(user_id))
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.get_json()
    
    if not data or not data.get('current_password') or not data.get('new_password'):
        return jsonify({'error': 'Missing passwords'}), 400
    
    if not user.check_password(data['current_password']):
        return jsonify({'error': 'Current password is incorrect'}), 401
    
    if len(data['new_password']) < 8:
        return jsonify({'error': 'New password must be at least 8 characters'}), 400
    
    user.set_password(data['new_password'])
    db.session.commit()
    
    return jsonify({'message': 'Password changed successfully'}), 200

@bp.route('/update-profile', methods=['PUT'])
@jwt_required()
def update_profile():
    """Update user profile (username and/or password)"""
    user_id = get_jwt_identity()
    user = User.query.get(int(user_id))
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
        
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
        
    current_password = data.get('current_password')
    new_username = data.get('username')
    new_password = data.get('new_password')
    
    if not current_password:
        return jsonify({'error': 'Current password is required to make profile changes'}), 400
        
    if not user.check_password(current_password):
        return jsonify({'error': 'Invalid current password'}), 401
        
    # Update username if provided and different
    if new_username and new_username != user.username:
        # Check if username already exists
        existing_user = User.query.filter_by(username=new_username).first()
        if existing_user:
            return jsonify({'error': 'Username already exists'}), 400
        user.username = new_username
        
    # Update password if provided
    if new_password:
        if len(new_password) < 8:
            return jsonify({'error': 'New password must be at least 8 characters'}), 400
        user.set_password(new_password)
        
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to update profile: {str(e)}'}), 500
        
    return jsonify({
        'message': 'Profile updated successfully',
        'user': user.to_dict()
    }), 200

@bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """Logout user (client should discard token)"""
    return jsonify({'message': 'Logged out successfully'}), 200

@bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    """Request password reset - send code via email"""
    data = request.get_json()
    
    if not data or not data.get('username'):
        return jsonify({ 'error': 'Username is required'}), 400
    
    user = User.query.filter_by(username=data['username']).first()
    
    if not user:
        # Don't reveal if user exists or not for security
        return jsonify({'message': 'If the username exists, a reset code will be sent'}), 200
    
    # Generate 6-digit reset code
    import secrets
    import string
    from datetime import datetime, timedelta
    
    reset_code = ''.join(secrets.choice(string.digits) for i in range(6))
    user.reset_token = reset_code
    user.reset_token_expires_at = datetime.utcnow() + timedelta(seconds=60)
    db.session.commit()
    
    # Send reset code via email
    from app.services.email_service import EmailService
    from app.models import SystemSettings
    
    email_service = EmailService()
    admin_email_setting = SystemSettings.query.filter_by(key='admin_email').first()
    
    if admin_email_setting and admin_email_setting.value:
        email_sent = email_service.send_password_reset(admin_email_setting.value, reset_code)
        
        if email_sent:
            # Mask email for response
            email = admin_email_setting.value
            masked_email = ""
            if '@' in email:
                local, domain = email.split('@')
                if '.' in domain:
                    domain_name, domain_ext = domain.rsplit('.', 1)
                    masked_local = local[:2] + '*' * (len(local) - 2) if len(local) > 2 else local
                    masked_domain = domain_name[:2] + '**' if len(domain_name) > 2 else domain_name
                    masked_email = f"{masked_local}@{masked_domain}.{domain_ext[:2]}**"
                else:
                    masked_local = local[:2] + '*' * (len(local) - 2) if len(local) > 2 else local
                    masked_email = f"{masked_local}@{domain[:2]}**"
            
            return jsonify({
                'message': 'Password reset code sent',
                'masked_email': masked_email
            }), 200
    
    return jsonify({'message': 'If the username exists, a reset code will be sent'}), 200


@bp.route('/verify-reset-code', methods=['POST'])
def verify_reset_code():
    """Verify reset code validity before resetting password"""
    data = request.get_json()
    
    if not data or not data.get('code'):
        return jsonify({'error': 'Reset code is required'}), 400
    
    from datetime import datetime
    user = User.query.filter_by(reset_token=data['code']).first()
    
    if not user:
        return jsonify({'error': 'Invalid or expired reset code'}), 400
    
    if not user.reset_token_expires_at or user.reset_token_expires_at < datetime.utcnow():
        return jsonify({'error': 'Reset code has expired'}), 400
        
    return jsonify({'message': 'Code verified successfully'}), 200


@bp.route('/reset-password', methods=['POST'])
def reset_password():
    """Verify reset code and update password"""
    data = request.get_json()
    
    if not data or not data.get('code') or not data.get('new_password'):
        return jsonify({'error': 'Reset code and new password are required'}), 400
    
    # Find user with matching reset token
    from datetime import datetime
    user = User.query.filter_by(reset_token=data['code']).first()
    
    if not user:
        return jsonify({'error': 'Invalid or expired reset code'}), 400
    
    # Check if token is expired
    if not user.reset_token_expires_at or user.reset_token_expires_at < datetime.utcnow():
        return jsonify({'error': 'Reset code has expired'}), 400
    
    # Update password
    user.set_password(data['new_password'])
    user.reset_token = None
    user.reset_token_expires_at = None
    db.session.commit()
    
    return jsonify({'message': 'Password updated successfully'}), 200
