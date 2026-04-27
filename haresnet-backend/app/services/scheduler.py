from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, time
import json
from app.models import Schedule, Device, DeviceTraffic, SystemSettings, Service
from app.services.nftables_manager import NftablesManager
from app.services.service_manager import ServiceManager
from app.services.device_discovery import DeviceDiscovery
from app import db
from app import socketio

class SchedulerService:
    """Background scheduler for time-based access control and monitoring"""
    
    def __init__(self, app):
        self.app = app
        self.scheduler = BackgroundScheduler()
        self.nft_manager = NftablesManager()
        self.device_discovery = DeviceDiscovery()
        self.last_counters = {} # ip -> {rx: bytes, tx: bytes}
    
    def start(self):
        """Start the scheduler"""
        # Check schedules at configurable interval (minutes)
        minutes = self.app.config.get('SCHEDULE_INTERVAL_MINUTES', 1)
        self.scheduler.add_job(
            func=self.check_schedules,
            trigger='interval',
            minutes=minutes,
            id='schedule_checker'
        )

        # Record device traffic at same interval
        self.scheduler.add_job(
            func=self.update_traffic_stats,
            trigger='interval',
            minutes=minutes,
            id='traffic_stats'
        )

        # Run device discovery very frequently (every 2 seconds)
        # This updates online status and finds new devices
        self.scheduler.add_job(
            func=self.run_device_discovery,
            trigger='interval',
            seconds=2,
            id='device_discovery'
        )

        # Refresh service IPs (DNS resolution) every 60 minutes
        self.scheduler.add_job(
            func=self.refresh_services,
            trigger='interval',
            minutes=60,
            id='service_refresh'
        )

        self.scheduler.start()
    
    def check_schedules(self):
        """Check and apply active schedules"""
        import os
        from zoneinfo import ZoneInfo
        from app.services.hostapd_manager import HostapdManager
        import sys
        
        hostapd_manager = HostapdManager()
        
        with self.app.app_context():
            try:
                # Get timezone from database or fallback to environment
                tz_setting = SystemSettings.query.filter_by(key='timezone').first()
                if tz_setting:
                    tz_name = tz_setting.value
                else:
                    tz_name = os.environ.get('TIMEZONE', 'UTC')
                    
                try:
                    tz = ZoneInfo(tz_name)
                except Exception:
                    tz = ZoneInfo('UTC')
                    print(f"[SCHEDULER] Invalid TIMEZONE {tz_name}, defaulting to UTC", flush=True)

                now = datetime.now(tz)
                current_time = now.time()
                current_day = now.strftime('%A').lower()
                
                print(f"[SCHEDULER] Checking schedules at {now.isoformat()} (day: {current_day}, time: {current_time})", flush=True)
                
                # Fetch all devices and enabled schedules
                devices = Device.query.all()
                enabled_schedules = Schedule.query.filter_by(enabled=True).all()
                
                # Group schedules by device_id
                device_schedules = {}
                for schedule in enabled_schedules:
                    if schedule.device_id not in device_schedules:
                        device_schedules[schedule.device_id] = []
                    device_schedules[schedule.device_id].append(schedule)
                
                changes_made = False
                
                for device in devices:
                    if not device.mac:
                        continue
                        
                    schedules = device_schedules.get(device.id, [])
                    if not schedules:
                        continue
                        
                    # Determine schedule types present for this device
                    has_allow_schedule = any(s.action == 'allow' for s in schedules)
                    has_block_schedule = any(s.action == 'block' for s in schedules)
                    
                    should_be_blocked = device.blocked # Default to current state if logic doesn't cover it
                    
                    # Logic:
                    # 1. If "Allow" schedules exist: Device is BLOCKED unless an "Allow" schedule is ACTIVE.
                    # 2. Else if "Block" schedules exist: Device is UNBLOCKED unless a "Block" schedule is ACTIVE.
                    
                    if has_allow_schedule:
                        # "Allow" mode: Default Blocked, Allow if active
                        is_allowed_now = False
                        msg_reason = "No active Allow schedule"
                        
                        for schedule in schedules:
                            if schedule.action != 'allow':
                                continue
                                
                            try:
                                days = json.loads(schedule.days) if schedule.days else []
                                if current_day not in [d.lower() for d in days]:
                                    continue

                                start = datetime.strptime(schedule.start_time, '%H:%M').time()
                                end = datetime.strptime(schedule.end_time, '%H:%M').time()
                                start_dt = datetime(now.year, now.month, now.day, start.hour, start.minute, tzinfo=tz)
                                end_dt = datetime(now.year, now.month, now.day, end.hour, end.minute, tzinfo=tz)
                                
                                is_active = False
                                if start_dt <= end_dt:
                                    is_active = start_dt <= now <= end_dt
                                else:
                                    is_active = now >= start_dt or now <= end_dt
                                    
                                if is_active:
                                    is_allowed_now = True
                                    msg_reason = f"Active Allow schedule {schedule.id}"
                                    break
                            except Exception as e:
                                print(f"[SCHEDULER] Error checking schedule {schedule.id}: {e}", flush=True)
                        
                        should_be_blocked = not is_allowed_now
                        # print(f"[SCHEDULER] Device {device.mac} Allow Mode: Active={is_allowed_now} -> Blocked={should_be_blocked} ({msg_reason})", flush=True)

                    elif has_block_schedule:
                        # "Block" mode: Default Unblocked, Block if active
                        is_blocked_now = False
                        msg_reason = "No active Block schedule"
                        
                        for schedule in schedules:
                            if schedule.action != 'block':
                                continue
                            
                            try:
                                days = json.loads(schedule.days) if schedule.days else []
                                if current_day not in [d.lower() for d in days]:
                                    continue

                                start = datetime.strptime(schedule.start_time, '%H:%M').time()
                                end = datetime.strptime(schedule.end_time, '%H:%M').time()
                                start_dt = datetime(now.year, now.month, now.day, start.hour, start.minute, tzinfo=tz)
                                end_dt = datetime(now.year, now.month, now.day, end.hour, end.minute, tzinfo=tz)
                                
                                is_active = False
                                if start_dt <= end_dt:
                                    is_active = start_dt <= now <= end_dt
                                else:
                                    is_active = now >= start_dt or now <= end_dt
                                    
                                if is_active:
                                    is_blocked_now = True
                                    msg_reason = f"Active Block schedule {schedule.id}"
                                    break
                            except Exception as e:
                                print(f"[SCHEDULER] Error checking schedule {schedule.id}: {e}", flush=True)
                        
                        should_be_blocked = is_blocked_now
                        # print(f"[SCHEDULER] Device {device.mac} Block Mode: Active={is_blocked_now} -> Blocked={should_be_blocked} ({msg_reason})", flush=True)
                    
                    # Apply state change if needed
                    if device.blocked != should_be_blocked:
                        print(f"[SCHEDULER] Changing device {device.mac} blocked status to {should_be_blocked}", flush=True)
                        device.blocked = should_be_blocked
                        db.session.add(device)
                        changes_made = True

                if changes_made:
                    db.session.commit()
                    print(f"[SCHEDULER] Database updated", flush=True)
                
                # ALWAYS apply firewall rules and hostapd deny list to ensure consistency
                try:
                    # print(f"[SCHEDULER] Syncing firewall rules...", flush=True)
                    self.nft_manager.apply_device_rules()
                    self.nft_manager.apply_child_safety_rules() # Ensure child safety rules persist
                    self.nft_manager.apply_service_blocking_rules() # Ensure service blocking rules persist
                    
                    blocked_devices = Device.query.filter_by(blocked=True).all()
                    blocked_macs = [d.mac for d in blocked_devices if d.mac]
                    hostapd_manager.update_deny_list(blocked_macs)
                    
                except Exception as e:
                    print(f"[SCHEDULER] Error applying firewall rules: {e}", flush=True)
                    import traceback
                    traceback.print_exc()
                    
            except Exception as e:
                print(f"[SCHEDULER] Critical error in check_schedules: {e}", flush=True)
                import traceback
                traceback.print_exc()

    def update_traffic_stats(self):
        """Poll nftables counters and save to DB"""
        with self.app.app_context():
            counters = self.nft_manager.get_counters()
            timestamp = datetime.utcnow()
            
            for ip, stats in counters.items():
                # Find device by IP
                device = Device.query.filter_by(ip=ip).first()
                if not device:
                    # Also try to ensure accounting rule exists for this IP if not present?
                    # No, we only track discovered devices for now.
                    continue
                
                # Calculate delta
                prev = self.last_counters.get(ip, {'rx': 0, 'tx': 0})
                
                # Handle counter reset (restart)
                if stats['rx'] < prev['rx'] or stats['tx'] < prev['tx']:
                     prev = {'rx': 0, 'tx': 0}
                
                delta_rx = stats['rx'] - prev['rx']
                delta_tx = stats['tx'] - prev['tx']
                
                # Update last counters
                self.last_counters[ip] = stats
                
                # Only save if there is traffic
                if delta_rx > 0 or delta_tx > 0:
                    traffic = DeviceTraffic(
                        device_id=device.id,
                        timestamp=timestamp,
                        bytes_received=delta_tx,  # Router TX = Device Download
                        bytes_sent=delta_rx       # Router RX = Device Upload
                    )
                    db.session.add(traffic)
                    # Emit realtime traffic update for frontend
                    try:
                        socketio.emit('device_traffic_update', {
                            'device_id': device.id,
                            'timestamp': timestamp.isoformat(),
                            'upload_bytes': delta_rx,
                            'download_bytes': delta_tx
                        })
                    except Exception:
                        pass
            
            # Commit all
            try:
                db.session.commit()
                
                # Prune old data (keep 24h)
                # This could be expensive if many rows, maybe run less frequently.
                # But decent for now.
                # DeviceTraffic.query.filter(DeviceTraffic.timestamp < (timestamp - timedelta(hours=24))).delete()
                # db.session.commit()
            except Exception as e:
                print(f"Error saving traffic stats: {e}")
                db.session.rollback()

    def stop(self):
        """Stop the scheduler"""
        self.scheduler.shutdown()

    def refresh_services(self):
        """Background task to refresh service IPs"""
        with self.app.app_context():
            try:
                print("[SCHEDULER] Refreshing service IPs...", flush=True)
                services = Service.query.filter_by(enabled=True).all()
                if not services:
                    return

                sm = ServiceManager()
                # has_changes = False # Unused
                
                for service in services:
                    sm.refresh_service_ips(service)
                
                db.session.commit()
                
                # Re-apply firewall rules
                self.nft_manager.apply_service_blocking_rules()
                print("[SCHEDULER] Service IPs refreshed and firewall rules updated", flush=True)
                
            except Exception as e:
                print(f"[SCHEDULER] Error refreshing services: {e}", flush=True)

    def run_device_discovery(self):
        """Background task to discover devices"""
        with self.app.app_context():
            try:
                self.device_discovery.update_device_database()
            except Exception as e:
                print(f"[SCHEDULER] Error in device discovery: {e}", flush=True)
