from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from app.services.nftables_manager import NftablesManager

bp = Blueprint('firewall', __name__)
nft_manager = NftablesManager()
from app.services.service_manager import ServiceManager
service_manager = ServiceManager()

@bp.route('/rules', methods=['GET'])
@jwt_required()
def get_rules():
    """Get active firewall rules"""
    try:
        rules = nft_manager.get_current_rules()
        return jsonify({
            'rules': rules
        }), 200
    except Exception as e:
        return jsonify({'error': f'Failed to get rules: {str(e)}'}), 500

@bp.route('/status', methods=['GET'])
@jwt_required()
def get_status():
    """Get firewall status"""
    try:
        status = nft_manager.get_status()
        return jsonify(status), 200
    except Exception as e:
        return jsonify({'error': f'Failed to get status: {str(e)}'}), 500

@bp.route('/apply', methods=['POST'])
@jwt_required()
def apply_rules():
    """Force apply all firewall rules"""
    try:
        nft_manager.initialize_firewall()
        nft_manager.apply_device_rules()
        nft_manager.apply_child_safety_rules()
        nft_manager.apply_service_blocking_rules()
        nft_manager.apply_ip_filter_rules()
        return jsonify({'message': 'Firewall rules applied successfully'}), 200
    except Exception as e:
        return jsonify({'error': f'Failed to apply rules: {str(e)}'}), 500


