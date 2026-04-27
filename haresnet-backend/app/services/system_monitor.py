import psutil
import time
import subprocess
import json
from datetime import datetime

class SystemMonitor:
    def __init__(self):
        self.last_net_io = psutil.net_io_counters()
        self.last_time = time.time()
        
    def get_stats(self):
        """Get current system statistics"""
        now = time.time()
        time_delta = now - self.last_time
        
        # CPU & Memory
        cpu_percent = psutil.cpu_percent(interval=None)
        memory = psutil.virtual_memory()

        # Disk usage (root partition)
        disk = psutil.disk_usage('/')

        # System uptime
        boot_time = psutil.boot_time()
        
        # Network Speed
        net_io = psutil.net_io_counters()
        
        if time_delta > 0:
            rx_bytes_per_sec = (net_io.bytes_recv - self.last_net_io.bytes_recv) / time_delta
            tx_bytes_per_sec = (net_io.bytes_sent - self.last_net_io.bytes_sent) / time_delta
        else:
            rx_bytes_per_sec = 0
            tx_bytes_per_sec = 0
            
        self.last_net_io = net_io
        self.last_time = now
        
        return {
            'cpu': {
                'percent': cpu_percent,
                'count': psutil.cpu_count()
            },
            'memory': {
                'percent': memory.percent,
                'total': memory.total,
                'used': memory.used
            },
            'disk': {
                'percent': disk.percent,
                'total': disk.total,
                'used': disk.used,
                'free': disk.free
            },
            'uptime': boot_time,
            'network': {
                'rx_bps': rx_bytes_per_sec * 8,
                'tx_bps': tx_bytes_per_sec * 8,
                'rx_bytes': net_io.bytes_recv,
                'tx_bytes': net_io.bytes_sent
            },
            'timestamp': datetime.now().isoformat()
        }

    def run_speedtest(self):
        """Perform internet speed test and broadcast results via Socket.IO"""
        from app import socketio
        import speedtest
        import traceback

        start_time = time.time()
        
        def emit(stage, progress=0, value=None, **kwargs):
            try:
                data = {
                    'stage': stage,
                    'progress': progress,
                    'overall_progress': progress,
                    'elapsed': round(time.time() - start_time, 1),
                    'value': value
                }
                data.update(kwargs)
                # Explicitly emit to the '/' namespace for maximum compatibility
                socketio.emit('speedtest_progress', data, namespace='/')
                socketio.sleep(0.01) # Yield to eventlet to ensure delivery
            except Exception as e:
                print(f"Error emitting speedtest progress: {e}")

        try:
            emit('server', 0)
            
            # Initialize speedtest-cli
            try:
                # Try secure=True first
                st = speedtest.Speedtest(secure=True)
            except Exception:
                # Fallback to non-secure if SSL issues occur
                st = speedtest.Speedtest(secure=False)
            
            st.get_best_server()
            server = st.best
            
            emit('server', 100, value=server)
            emit('ping', 100, value=st.results.ping)
            
            # Download Test with Progress callback
            def download_callback(current, total, start=False, end=False):
                if not start and not end:
                    percent = int((current / total) * 100)
                    # Emit every 10% to avoid flooding
                    if percent % 10 == 0:
                        emit('download', percent, value=current)

            emit('download', 5) # Initial indicator
            st.download(callback=download_callback)
            
            results = st.results.dict()
            emit('download', 100, value=results['download'])
            
            # Upload Test with Progress callback
            def upload_callback(current, total, start=False, end=False):
                if not start and not end:
                    percent = int((current / total) * 100)
                    if percent % 10 == 0:
                        emit('upload', percent, value=current)

            emit('upload', 5) # Initial indicator
            st.upload(callback=upload_callback)
            
            results = st.results.dict()
            emit('upload', 100, value=results['upload'])
            
            final_results = {
                'download_mbps': round(results['download'] / 1_000_000, 2),
                'upload_mbps': round(results['upload'] / 1_000_000, 2),
                'ping': round(st.results.ping, 2),
                'server': server,
                'client': results['client'],
                'timestamp': results['timestamp'],
                'duration': round(time.time() - start_time, 2)
            }
            
            socketio.emit('speedtest_finish', final_results, namespace='/')
            socketio.sleep(0.5)
            return final_results
            
        except Exception as e:
            traceback.print_exc()
            socketio.emit('speedtest_error', {'error': str(e)}, namespace='/')
            raise e

# Global instance
monitor = SystemMonitor()
