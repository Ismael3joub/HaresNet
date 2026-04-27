from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required

bp = Blueprint('network', __name__)

@bp.route('/config', methods=['GET'])
@jwt_required()
def get_config():
    """Get current network configuration (router-only)"""
    # Always return router mode
    return jsonify({'mode': 'router'}), 200
