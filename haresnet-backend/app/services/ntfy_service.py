import os
import requests
import json
from flask import current_app

class NtfyService:
    def __init__(self):
        # Fetch topic from DB, fallback to env
        try:
            from app.models import SystemSettings
            # Use current_app.app_context() if outside request context
            # However, services are usually initialized within app context or proper scope
            # NtfyService is lightweight, so we can query DB on demand or init
            # But let's check if we have app context
            if current_app:
                 try:
                     setting = SystemSettings.query.filter_by(key='ntfy_topic').first()
                     topic_from_db = setting.value if setting else None
                 except Exception:
                     topic_from_db = None
            else:
                 topic_from_db = None

            if topic_from_db:
                self.topic = topic_from_db
            elif os.environ.get('NTFY_TOPIC'):
                self.topic = os.environ.get('NTFY_TOPIC')
            else:
                # Generate unique default topic based on MAC address
                import uuid
                mac_num = uuid.getnode()
                mac_hex = ':'.join(('%012X' % mac_num)[i:i+2] for i in range(0, 12, 2))
                # Generate unique default topic based on MAC address
                import uuid
                mac_num = uuid.getnode()
                mac_hex = ':'.join(('%012X' % mac_num)[i:i+2] for i in range(0, 12, 2))
                unique_suffix = mac_hex.replace(':', '').lower()[-6:] # Last 6 chars of MAC
                self.topic = f"haresnet_{unique_suffix}"
                print(f"[NtfyService] Using auto-generated unique topic: {self.topic}", flush=True)

        except Exception as e:
            print(f"[NtfyService] Init error: {e}", flush=True)
            self.topic = "haresnet_fallback"
            
        self.base_url = "https://ntfy.sh"

    def send_notification(self, title, message, priority='default', tags=None):
        """
        Send a notification to ntfy.sh
        priority: min, low, default, high, max
        tags: list of tags (emojis or strings)
        """
        if not self.topic:
            print("[NtfyService] No topic configured, skipping notification", flush=True)
            return False

        headers = {
            "Title": title,
            "Priority": priority,
        }
        
        if tags:
            headers["Tags"] = ",".join(tags)

        try:
            url = f"{self.base_url}/{self.topic}"
            response = requests.post(
                url,
                data=message.encode('utf-8'),
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            print(f"[NtfyService] Notification sent: {title}", flush=True)
            return True
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                print(f"[NtfyService] Rate limited (429). The topic '{self.topic}' is too busy. Please change NTFY_TOPIC in settings.", flush=True)
            else:
                print(f"[NtfyService] HTTP Error: {str(e)}", flush=True)
            return False
        except Exception as e:
            print(f"[NtfyService] Failed to send notification: {str(e)}", flush=True)
            return False

    def send_otp(self, code):
        """Send OTP code via NTFY"""
        return self.send_notification(
            title="HaresNet Login Code",
            message=f"Your login code is: {code}",
            priority="high",
            tags=["lock", "key"]
        )

    def notify_new_device(self, device):
        """Notify about new device"""
        name = device.hostname or "Unknown Device"
        return self.send_notification(
            title="New Device Connected",
            message=f"Device: {name}\nMAC: {device.mac}\nIP: {device.ip}",
            priority="default",
            tags=["new", "computer"]
        )

    def notify_traffic_spike(self, device, rate_mbps):
        """Notify about traffic spike"""
        name = device.hostname or "Unknown Device"
        return self.send_notification(
            title="High Traffic Alert",
            message=f"Device {name} ({device.mac}) is using {rate_mbps:.2f} Mbps",
            priority="high",
            tags=["warning", "chart_with_upwards_trend"]
        )
    def notify_traffic_limit_exceeded(self, device, limit_type, current_usage_mb, limit_mb):
        """Notify about traffic limit exceeded"""
        name = device.hostname or "Unknown Device"
        limit_name = "Daily" if limit_type == 'daily' else "Hourly"
        
        return self.send_notification(
            title=f"Traffic Limit Exceeded: {name}",
            message=f"Device {name} ({device.mac}) has used {current_usage_mb:.2f} MB, exceeding the {limit_name} limit of {limit_mb} MB.",
            priority="high",
            tags=["rotating_light", "warning"]
        )
