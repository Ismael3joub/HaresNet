from datetime import datetime, timedelta
from app import db
from app.models import Device, DeviceTraffic
from app.services.nftables_manager import NftablesManager
from flask import current_app


class TrafficMonitor:
    """Monitors and records device network traffic"""
    
    def __init__(self):
        self.nft_manager = NftablesManager()
        # Store previous counter values to calculate deltas
        # Structure: {ip: {'tx': bytes, 'rx': bytes}}
        self.previous_counters = {}
        
        # Initialize InfluxDB service (optional)
        self.influxdb = None
        try:
            from app.services.influxdb_service import InfluxDBService
            self.influxdb = InfluxDBService()
            if self.influxdb.is_connected():
                print("[TrafficMonitor] InfluxDB integration enabled", flush=True)
            else:
                print("[TrafficMonitor] InfluxDB not available, using SQLite only", flush=True)
        except Exception as e:
            print(f"[TrafficMonitor] InfluxDB initialization failed: {str(e)}", flush=True)
            self.influxdb = None

    
    def collect_traffic_stats(self):
        """
        Collect traffic statistics for all devices.
        Reads nftables counters, calculates deltas, and stores in database in a single transaction.
        """
        try:
            # Get current counter values from nftables
            current_counters = self.nft_manager.get_counters()
            
            if not current_counters:
                return
            
            now = datetime.utcnow()
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            hour_start = now.replace(minute=0, second=0, microsecond=0)
            
            # Pre-fetch all devices to avoid per-IP queries
            devices = {d.ip: d for d in Device.query.all() if d.ip}
            
            # Step 1: Calculate deltas and prepare entries
            for ip, counters in current_counters.items():
                device = devices.get(ip)
                if not device:
                    continue
                    
                tx_bytes = counters.get('tx', 0)
                rx_bytes = counters.get('rx', 0)
                
                if ip in self.previous_counters:
                    prev_tx = self.previous_counters[ip]['tx']
                    prev_rx = self.previous_counters[ip]['rx']
                    
                    delta_tx = max(0, tx_bytes - prev_tx) if tx_bytes >= prev_tx else tx_bytes
                    delta_rx = max(0, rx_bytes - prev_rx) if rx_bytes >= prev_rx else rx_bytes
                    
                    if delta_tx > 0 or delta_rx > 0:
                        # Prepare SQLite entry
                        traffic_entry = DeviceTraffic(
                            device_id=device.id,
                            timestamp=now,
                            bytes_sent=delta_tx,
                            bytes_received=delta_rx
                        )
                        db.session.add(traffic_entry)
                        
                        # Write to InfluxDB (independent of SQLite transaction)
                        if self.influxdb and self.influxdb.is_connected():
                            try:
                                self.influxdb.write_traffic_point(
                                    device_id=device.id, mac=device.mac,
                                    hostname=device.hostname, ip=device.ip,
                                    upload_bytes=delta_tx, download_bytes=delta_rx,
                                    timestamp=now
                                )
                            except Exception:
                                pass

                        # Optimization: Traffic limits and spikes checked after commit or with session info
                        # For now, we'll keep the logic but ensure it doesn't trigger extra flushes if possible
                        
                        # NTFY Spike Check (local calculation, no DB needed yet)
                        threshold_mbps = current_app.config.get('TRAFFIC_THRESHOLD_MBPS', 10.0)
                        rate_mbps = ((delta_tx + delta_rx) * 8) / (1024 * 1024)
                        if rate_mbps > threshold_mbps:
                            try:
                                from app.services.ntfy_service import NtfyService
                                NtfyService().notify_traffic_spike(device, rate_mbps)
                            except Exception: pass

                # Update memory counters
                self.previous_counters[ip] = {'tx': tx_bytes, 'rx': rx_bytes}
            
            # Step 2: Atomic Commit for all traffic records
            db.session.commit()
            
            # Step 3: Cleanup old data (only occasionally)
            if now.minute % 15 == 0 and now.second < 20: # Every 15 mins
                self._cleanup_old_data()
            
            return True
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"[TrafficMonitor] Error: {str(e)}")
            return False
        finally:
            db.session.remove()
    
    def _cleanup_old_data(self):
        """
        Remove traffic data older than retention period.
        Default: 7 days
        """
        try:
            retention_days = current_app.config.get('TRAFFIC_RETENTION_DAYS', 7)
            cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
            
            # Delete old records
            deleted_count = DeviceTraffic.query.filter(
                DeviceTraffic.timestamp < cutoff_date
            ).delete()
            
            if deleted_count > 0:
                db.session.commit()
                print(f"[TrafficMonitor] Cleaned up {deleted_count} old traffic records")
        
        except Exception as e:
            db.session.rollback()
            print(f"[TrafficMonitor] Error during cleanup: {str(e)}")
    
    def get_device_stats(self, device_id, hours=24):
        """
        Get traffic statistics for a specific device.
        
        Args:
            device_id: Device ID
            hours: Number of hours to look back (default: 24)
        
        Returns:
            dict with total upload/download and time series data
        """
        since = datetime.utcnow() - timedelta(hours=hours)
        
        traffic_records = DeviceTraffic.query.filter(
            DeviceTraffic.device_id == device_id,
            DeviceTraffic.timestamp >= since
        ).order_by(DeviceTraffic.timestamp.asc()).all()
        
        # Calculate totals
        total_upload = sum(t.bytes_sent for t in traffic_records)
        total_download = sum(t.bytes_received for t in traffic_records)
        
        return {
            'device_id': device_id,
            'period_hours': hours,
            'total_upload': total_upload,
            'total_download': total_download,
            'total_upload_formatted': self._format_bytes(total_upload),
            'total_download_formatted': self._format_bytes(total_download),
            'data_points': len(traffic_records),
            'time_series': [t.to_dict() for t in traffic_records]
        }
    
    def get_current_rates(self):
        """
        Get current upload/download rates for all active devices.
        Based on the most recent traffic measurements.
        
        Returns:
            dict of {device_id: {'upload_rate': bytes/sec, 'download_rate': bytes/sec}}
        """
        try:
            # Get the most recent traffic entries (within last minute)
            since = datetime.utcnow() - timedelta(minutes=1)
            
            # Group by device and get latest 2 entries to calculate rate
            rates = {}
            devices = Device.query.all()
            
            for device in devices:
                recent_traffic = DeviceTraffic.query.filter(
                    DeviceTraffic.device_id == device.id,
                    DeviceTraffic.timestamp >= since
                ).order_by(DeviceTraffic.timestamp.desc()).limit(2).all()
                
                if len(recent_traffic) >= 2:
                    latest = recent_traffic[0]
                    previous = recent_traffic[1]
                    
                    # Calculate time delta in seconds
                    time_delta = (latest.timestamp - previous.timestamp).total_seconds()
                    
                    if time_delta > 0:
                        upload_rate = latest.bytes_sent / time_delta
                        download_rate = latest.bytes_received / time_delta
                        
                        rates[device.id] = {
                            'device_id': device.id,
                            'mac': device.mac,
                            'hostname': device.hostname,
                            'upload_rate': upload_rate,
                            'download_rate': download_rate,
                            'upload_rate_formatted': f"{self._format_bytes(upload_rate)}/s",
                            'download_rate_formatted': f"{self._format_bytes(download_rate)}/s"
                        }
            
            return rates
            
        except Exception as e:
            print(f"[TrafficMonitor] Error calculating rates: {str(e)}")
            return {}
    
    @staticmethod
    def _format_bytes(bytes_val):
        """Format bytes into human-readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_val < 1024.0:
                return f"{bytes_val:.2f} {unit}"
            bytes_val /= 1024.0
        return f"{bytes_val:.2f} PB"
