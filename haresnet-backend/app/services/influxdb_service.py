import os
from datetime import datetime, timedelta
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from flask import current_app


class InfluxDBService:
    """Service for managing time-series traffic data in InfluxDB"""
    
    def __init__(self):
        """Initialize InfluxDB client"""
        self.url = os.environ.get('INFLUXDB_URL', 'http://localhost:8086')
        self.token = os.environ.get('INFLUXDB_TOKEN', 'haresnet_super_secret_token_change_in_production')
        self.org = os.environ.get('INFLUXDB_ORG', 'haresnet')
        self.bucket = os.environ.get('INFLUXDB_BUCKET', 'traffic')
        
        self.client = None
        self.write_api = None
        self.query_api = None
        self._connected = False
        
        self._connect()
    
    def _connect(self):
        """Establish connection to InfluxDB"""
        try:
            self.client = InfluxDBClient(
                url=self.url,
                token=self.token,
                org=self.org,
                timeout=10_000
            )
            self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
            self.query_api = self.client.query_api()
            
            # Test connection
            health = self.client.health()
            if health.status == "pass":
                self._connected = True
                print(f"[InfluxDB] ✓ Connected to {self.url}", flush=True)
            else:
                print(f" Warning: InfluxDB health check returned: {health.status}", flush=True)
                
        except Exception as e:
            self._connected = False
            print(f"[InfluxDB] ✗ Connection failed: {str(e)}", flush=True)
            print(f"[InfluxDB] Traffic data will not be stored in InfluxDB", flush=True)
    
    def is_connected(self):
        """Check if connected to InfluxDB"""
        return self._connected
    
    def write_traffic_point(self, device_id, mac, hostname, ip, upload_bytes, download_bytes, timestamp=None):
        """
        Write a single traffic data point to InfluxDB
        
        Args:
            device_id: Database device ID
            mac: Device MAC address
            hostname: Device hostname
            ip: Device IP address
            upload_bytes: Bytes uploaded (delta)
            download_bytes: Bytes downloaded (delta)
            timestamp: UTC timestamp (defaults to now)
        """
        if not self._connected:
            return False
        
        try:
            if timestamp is None:
                timestamp = datetime.utcnow()
            
            # Create data point
            point = Point("device_traffic") \
                .tag("device_id", str(device_id)) \
                .tag("mac", mac or "unknown") \
                .tag("hostname", hostname or "unknown") \
                .tag("ip", ip or "unknown") \
                .field("upload_bytes", int(upload_bytes)) \
                .field("download_bytes", int(download_bytes)) \
                .time(timestamp, WritePrecision.S)
            
            # Write to InfluxDB
            self.write_api.write(bucket=self.bucket, org=self.org, record=point)
            return True
            
        except Exception as e:
            print(f"[InfluxDB] Error writing traffic point: {str(e)}", flush=True)
            return False
    
    def write_traffic_batch(self, traffic_points):
        """
        Write multiple traffic points in a batch
        
        Args:
            traffic_points: List of dicts with keys: device_id, mac, hostname, ip, upload_bytes, download_bytes, timestamp
        """
        if not self._connected or not traffic_points:
            return False
        
        try:
            points = []
            for tp in traffic_points:
                point = Point("device_traffic") \
                    .tag("device_id", str(tp['device_id'])) \
                    .tag("mac", tp.get('mac', 'unknown')) \
                    .tag("hostname", tp.get('hostname', 'unknown')) \
                    .tag("ip", tp.get('ip', 'unknown')) \
                    .field("upload_bytes", int(tp['upload_bytes'])) \
                    .field("download_bytes", int(tp['download_bytes'])) \
                    .time(tp.get('timestamp', datetime.utcnow()), WritePrecision.S)
                points.append(point)
            
            self.write_api.write(bucket=self.bucket, org=self.org, record=points)
            return True
            
        except Exception as e:
            print(f"[InfluxDB] Error writing batch: {str(e)}", flush=True)
            return False
    
    def query_device_traffic(self, device_id, start_time, end_time=None, aggregate_window=None):
        """
        Query traffic data for a specific device
        
        Args:
            device_id: Database device ID
            start_time: Start time (datetime or ISO string)
            end_time: End time (datetime or ISO string), defaults to now
            aggregate_window: Aggregation window (e.g., "1m", "5m", "1h", "1d"), None for raw data
            
        Returns:
            List of dicts with timestamp, upload, download
        """
        if not self._connected:
            return []
        
        try:
            if end_time is None:
                end_time = datetime.utcnow()
            
            # Convert to RFC3339 format
            if isinstance(start_time, datetime):
                start_str = start_time.strftime('%Y-%m-%dT%H:%M:%SZ')
            else:
                start_str = start_time
                
            if isinstance(end_time, datetime):
                end_str = end_time.strftime('%Y-%m-%dT%H:%M:%SZ')
            else:
                end_str = end_time
            
            # Build Flux query
            if aggregate_window:
                # Aggregated query
                query = f'''
                from(bucket: "{self.bucket}")
                  |> range(start: {start_str}, stop: {end_str})
                  |> filter(fn: (r) => r["_measurement"] == "device_traffic")
                  |> filter(fn: (r) => r["device_id"] == "{device_id}")
                  |> filter(fn: (r) => r["_field"] == "upload_bytes" or r["_field"] == "download_bytes")
                  |> aggregateWindow(every: {aggregate_window}, fn: sum, createEmpty: false)
                  |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
                '''
            else:
                # Raw data query
                query = f'''
                from(bucket: "{self.bucket}")
                  |> range(start: {start_str}, stop: {end_str})
                  |> filter(fn: (r) => r["_measurement"] == "device_traffic")
                  |> filter(fn: (r) => r["device_id"] == "{device_id}")
                  |> filter(fn: (r) => r["_field"] == "upload_bytes" or r["_field"] == "download_bytes")
                  |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
                '''
            
            # Execute query
            tables = self.query_api.query(query, org=self.org)
            
            # Parse results
            results = []
            for table in tables:
                for record in table.records:
                    results.append({
                        'timestamp': record.get_time().isoformat(),
                        'upload': int(record.values.get('upload_bytes', 0)),
                        'download': int(record.values.get('download_bytes', 0))
                    })
            
            return results
            
        except Exception as e:
            print(f"[InfluxDB] Error querying device traffic: {str(e)}", flush=True)
            import traceback
            traceback.print_exc()
            return []
    
    def query_network_traffic(self, start_time, end_time=None, aggregate_window=None):
        """
        Query total network traffic (all devices combined)
        
        Args:
            start_time: Start time (datetime or ISO string)
            end_time: End time (datetime or ISO string), defaults to now
            aggregate_window: Aggregation window (e.g., "1m", "5m", "1h", "1d")
            
        Returns:
            List of dicts with timestamp, upload, download
        """
        if not self._connected:
            return []
        
        try:
            if end_time is None:
                end_time = datetime.utcnow()
            
            # Convert to RFC3339 format
            if isinstance(start_time, datetime):
                start_str = start_time.strftime('%Y-%m-%dT%H:%M:%SZ')
            else:
                start_str = start_time
                
            if isinstance(end_time, datetime):
                end_str = end_time.strftime('%Y-%m-%dT%H:%M:%SZ')
            else:
                end_str = end_time
            
            # Build Flux query - sum across all devices
            if aggregate_window:
                query = f'''
                from(bucket: "{self.bucket}")
                  |> range(start: {start_str}, stop: {end_str})
                  |> filter(fn: (r) => r["_measurement"] == "device_traffic")
                  |> filter(fn: (r) => r["_field"] == "upload_bytes" or r["_field"] == "download_bytes")
                  |> aggregateWindow(every: {aggregate_window}, fn: sum, createEmpty: false)
                  |> group(columns: ["_time", "_field"])
                  |> sum()
                  |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
                '''
            else:
                query = f'''
                from(bucket: "{self.bucket}")
                  |> range(start: {start_str}, stop: {end_str})
                  |> filter(fn: (r) => r["_measurement"] == "device_traffic")
                  |> filter(fn: (r) => r["_field"] == "upload_bytes" or r["_field"] == "download_bytes")
                  |> group(columns: ["_time", "_field"])
                  |> sum()
                  |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
                '''
            
            # Execute query
            tables = self.query_api.query(query, org=self.org)
            
            # Parse results
            results = []
            for table in tables:
                for record in table.records:
                    results.append({
                        'timestamp': record.get_time().isoformat(),
                        'upload': int(record.values.get('upload_bytes', 0)),
                        'download': int(record.values.get('download_bytes', 0))
                    })
            
            return results
            
        except Exception as e:
            print(f"[InfluxDB] Error querying network traffic: {str(e)}", flush=True)
            return []
    
    def get_device_stats(self, device_id, hours=24):
        """
        Get aggregated statistics for a device
        
        Args:
            device_id: Database device ID
            hours: Number of hours to look back
            
        Returns:
            Dict with total_upload, total_download, avg_upload_rate, avg_download_rate
        """
        if not self._connected:
            return None
        
        try:
            start_time = datetime.utcnow() - timedelta(hours=hours)
            
            query = f'''
            from(bucket: "{self.bucket}")
              |> range(start: -{hours}h)
              |> filter(fn: (r) => r["_measurement"] == "device_traffic")
              |> filter(fn: (r) => r["device_id"] == "{device_id}")
              |> filter(fn: (r) => r["_field"] == "upload_bytes" or r["_field"] == "download_bytes")
              |> group(columns: ["_field"])
              |> sum()
            '''
            
            tables = self.query_api.query(query, org=self.org)
            
            total_upload = 0
            total_download = 0
            
            for table in tables:
                for record in table.records:
                    field = record.get_field()
                    value = record.get_value()
                    
                    if field == "upload_bytes":
                        total_upload = int(value)
                    elif field == "download_bytes":
                        total_download = int(value)
            
            # Calculate average rates (bytes per second)
            duration_seconds = hours * 3600
            avg_upload_rate = total_upload / duration_seconds if duration_seconds > 0 else 0
            avg_download_rate = total_download / duration_seconds if duration_seconds > 0 else 0
            
            return {
                'total_upload': total_upload,
                'total_download': total_download,
                'avg_upload_rate': avg_upload_rate,
                'avg_download_rate': avg_download_rate,
                'period_hours': hours
            }
            
        except Exception as e:
            print(f"[InfluxDB] Error getting device stats: {str(e)}", flush=True)
            return None
    
    def get_top_devices(self, limit=10, hours=24, sort_by='total'):
        """
        Get top devices by traffic
        
        Args:
            limit: Number of devices to return
            hours: Time period to analyze
            sort_by: 'total', 'upload', or 'download'
            
        Returns:
            List of dicts with device_id, mac, hostname, total_traffic, upload, download
        """
        if not self._connected:
            return []
        
        try:
            query = f'''
            from(bucket: "{self.bucket}")
              |> range(start: -{hours}h)
              |> filter(fn: (r) => r["_measurement"] == "device_traffic")
              |> filter(fn: (r) => r["_field"] == "upload_bytes" or r["_field"] == "download_bytes")
              |> group(columns: ["device_id", "mac", "hostname", "_field"])
              |> sum()
              |> pivot(rowKey:["device_id", "mac", "hostname"], columnKey: ["_field"], valueColumn: "_value")
            '''
            
            tables = self.query_api.query(query, org=self.org)
            
            devices = []
            for table in tables:
                for record in table.records:
                    upload = int(record.values.get('upload_bytes', 0))
                    download = int(record.values.get('download_bytes', 0))
                    total = upload + download
                    
                    devices.append({
                        'device_id': record.values.get('device_id'),
                        'mac': record.values.get('mac'),
                        'hostname': record.values.get('hostname'),
                        'upload': upload,
                        'download': download,
                        'total': total
                    })
            
            # Sort by requested field
            if sort_by == 'upload':
                devices.sort(key=lambda x: x['upload'], reverse=True)
            elif sort_by == 'download':
                devices.sort(key=lambda x: x['download'], reverse=True)
            else:  # total
                devices.sort(key=lambda x: x['total'], reverse=True)
            
            return devices[:limit]
            
        except Exception as e:
            print(f"[InfluxDB] Error getting top devices: {str(e)}", flush=True)
            return []
    
    def close(self):
        """Close InfluxDB connection"""
        if self.client:
            try:
                self.client.close()
                print("[InfluxDB] Connection closed", flush=True)
            except Exception as e:
                print(f"[InfluxDB] Error closing connection: {str(e)}", flush=True)
