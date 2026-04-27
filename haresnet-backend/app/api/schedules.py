from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app import db
from app.models import Schedule, Device
import json
from datetime import datetime
import os
from zoneinfo import ZoneInfo
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app import db
from app.models import Schedule, Device, SystemSettings
import json
from datetime import datetime, timedelta
import os
from zoneinfo import ZoneInfo
from app.services.nftables_manager import NftablesManager

bp = Blueprint('schedules', __name__)


def _get_timezone():
    try:
        tz_setting = SystemSettings.query.filter_by(key='timezone').first()
        tz_name = tz_setting.value if tz_setting and tz_setting.value else os.environ.get('TIMEZONE', 'UTC')
    except Exception:
        tz_name = os.environ.get('TIMEZONE', 'UTC')
    try:
        return ZoneInfo(tz_name)
    except Exception:
        return ZoneInfo('UTC')


def _is_schedule_active(sched, tz=None):
    if not tz:
        tz = _get_timezone()

    now = datetime.now(tz)

    try:
        days = json.loads(sched.days) if sched.days else []
    except Exception:
        days = []

    if now.strftime('%A').lower() not in [d.lower() for d in days]:
        return False

    try:
        start = datetime.strptime(sched.start_time, '%H:%M').time()
        end = datetime.strptime(sched.end_time, '%H:%M').time()
    except Exception:
        return False

    # Build timezone-aware datetimes for today
    start_dt = datetime(now.year, now.month, now.day, start.hour, start.minute, tzinfo=tz)
    end_dt = datetime(now.year, now.month, now.day, end.hour, end.minute, tzinfo=tz)

    if start_dt <= end_dt:
        return start_dt <= now <= end_dt
    else:
        # Spans midnight: active if now >= start_dt OR now <= end_dt
        return now >= start_dt or now <= end_dt


def _evaluate_device_schedules(device_id):
    """Trigger global schedule check"""
    # Use the centralized SchedulerService logic to ensure consistency
    from app.services.scheduler import SchedulerService
    try:
        from flask import current_app
        # We need to run this in a way that doesn't duplicate the scheduler's job,
        # but re-using the logic is safer than duplicating it.
        # check_schedules() iterates ALL devices. This might be slightly inefficient
        # for a single device update, but it guarantees correctness.
        # Given the small number of devices (dozens), this is negligible.
        
        scheduler = SchedulerService(current_app)
        scheduler.check_schedules()
        return True
    except Exception as e:
        print(f"[SCHEDULE] Error evaluating schedules: {e}")
        return False


@bp.route('/evaluate', methods=['POST'])
@jwt_required()
def evaluate_all_schedules():
    """Manually trigger schedule evaluation for testing"""
    from app.services.scheduler import SchedulerService
    from flask import current_app
    
    try:
        # Get app context
        with current_app.app_context():
            scheduler = SchedulerService(current_app)
            scheduler.check_schedules()
        
        return jsonify({
            'message': 'Schedules evaluated successfully'
        }), 200
    except Exception as e:
        return jsonify({
            'error': f'Failed to evaluate schedules: {str(e)}'
        }), 500


@bp.route('', methods=['GET'])
@jwt_required()
def get_schedules():
    """Get all schedules"""
    device_id = request.args.get('device_id', type=int)

    query = Schedule.query

    if device_id:
        query = query.filter_by(device_id=device_id)

    schedules = query.order_by(Schedule.created_at.desc()).all()

    return jsonify({
        'schedules': [schedule.to_dict() for schedule in schedules],
        'total': len(schedules)
    }), 200


@bp.route('', methods=['POST'])
@jwt_required()
def create_schedule():
    """Create new schedule"""
    data = request.get_json()

    if not data or not data.get('device_id'):
        return jsonify({'error': 'Missing device_id'}), 400

    device = Device.query.get(data['device_id'])
    if not device:
        return jsonify({'error': 'Device not found'}), 404

    # Validate required fields
    required_fields = ['name', 'days', 'start_time', 'end_time', 'action']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing {field}'}), 400

    # Validate data
    if data['action'] not in ['block', 'allow']:
        return jsonify({'error': 'Action must be "block" or "allow"'}), 400

    # Create schedule
    schedule = Schedule(
        device_id=data['device_id'],
        name=data['name'],
        days=json.dumps(data['days']),
        start_time=data['start_time'],
        end_time=data['end_time'],
        action=data['action'],
        enabled=data.get('enabled', True)
    )

    db.session.add(schedule)
    db.session.commit()

    # Evaluate schedules for this device immediately
    try:
        _evaluate_device_schedules(device.id)
    except Exception as e:
        print(f"Error evaluating schedules after create: {e}")

    return jsonify({
        'message': 'Schedule created successfully',
        'schedule': schedule.to_dict()
    }), 201


@bp.route('/<int:schedule_id>', methods=['PUT'])
@jwt_required()
def update_schedule(schedule_id):
    """Update schedule"""
    schedule = Schedule.query.get(schedule_id)

    if not schedule:
        return jsonify({'error': 'Schedule not found'}), 404

    data = request.get_json()

    if 'name' in data:
        schedule.name = data['name']

    if 'days' in data:
        schedule.days = json.dumps(data['days'])

    if 'start_time' in data:
        schedule.start_time = data['start_time']

    if 'end_time' in data:
        schedule.end_time = data['end_time']

    if 'action' in data:
        if data['action'] not in ['block', 'allow']:
            return jsonify({'error': 'Action must be "block" or "allow"'}), 400
        schedule.action = data['action']

    if 'enabled' in data:
        schedule.enabled = data['enabled']

    db.session.commit()

    # Re-evaluate schedules for device immediately
    try:
        _evaluate_device_schedules(schedule.device_id)
    except Exception as e:
        print(f"Error evaluating schedules after update: {e}")

    return jsonify({
        'message': 'Schedule updated successfully',
        'schedule': schedule.to_dict()
    }), 200


@bp.route('/<int:schedule_id>', methods=['DELETE'])
@jwt_required()
def delete_schedule(schedule_id):
    """Delete schedule"""
    schedule = Schedule.query.get(schedule_id)

    if not schedule:
        return jsonify({'error': 'Schedule not found'}), 404

    device_id = schedule.device_id
    db.session.delete(schedule)
    db.session.commit()

    # Re-evaluate schedules for device after deletion
    try:
        _evaluate_device_schedules(device_id)
    except Exception as e:
        print(f"Error evaluating schedules after delete: {e}")

    return jsonify({'message': 'Schedule deleted successfully'}), 200


@bp.route('/<int:schedule_id>/toggle', methods=['POST'])
@jwt_required()
def toggle_schedule(schedule_id):
    """Enable/disable schedule"""
    schedule = Schedule.query.get(schedule_id)

    if not schedule:
        return jsonify({'error': 'Schedule not found'}), 404

    schedule.enabled = not schedule.enabled
    db.session.commit()

    # Re-evaluate device schedules after toggle
    try:
        _evaluate_device_schedules(schedule.device_id)
    except Exception as e:
        print(f"Error evaluating schedules after toggle: {e}")

    return jsonify({
        'message': f'Schedule {"enabled" if schedule.enabled else "disabled"}',
        'schedule': schedule.to_dict()
    }), 200
