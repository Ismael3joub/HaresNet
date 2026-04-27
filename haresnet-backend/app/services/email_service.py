import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import current_app
from app.models import SystemSettings
import os

class EmailService:
    def __init__(self):
        # Gmail SMTP configuration
        self.host = 'smtp.gmail.com'
        self.port = 587
        self.username = 'ismaelrjoub414@gmail.com'
        self.password = 'shtf vrtt wjzx icpl'
        self.sender_email = 'ismaelrjoub414@gmail.com'

    def send_email(self, to_email, subject, body_text, body_html=None):
        """Send an email with optional HTML content"""
        try:
            msg = MIMEMultipart('alternative')
            msg['From'] = self.sender_email
            msg['To'] = to_email
            msg['Subject'] = subject

            # Attach plain text version
            part1 = MIMEText(body_text, 'plain')
            msg.attach(part1)

            # Attach HTML version if provided
            if body_html:
                part2 = MIMEText(body_html, 'html')
                msg.attach(part2)

            # Connect to Gmail SMTP server with TLS
            with smtplib.SMTP(self.host, self.port) as server:
                server.starttls()  # Upgrade to secure connection
                server.login(self.username, self.password)
                server.send_message(msg)
            
            print(f"[EmailService] Email sent to {to_email}", flush=True)
            return True
        except Exception as e:
            print(f"[EmailService] Failed to send email: {str(e)}", flush=True)
            return False

    def _load_template(self, template_name, **kwargs):
        """Load and render an HTML email template"""
        try:
            template_path = os.path.join(os.path.dirname(__file__), '..', 'templates', template_name)
            with open(template_path, 'r') as f:
                template = f.read()
            
            # Simple template replacement
            for key, value in kwargs.items():
                template = template.replace(f'{{{{ {key} }}}}', str(value))
            
            return template
        except Exception as e:
            print(f"[EmailService] Failed to load template {template_name}: {str(e)}", flush=True)
            return None

    def send_otp(self, otp_code):
        """Send OTP to the configured admin email with HTML template"""
        try:
            # Fetch admin email from settings
            setting = SystemSettings.query.filter_by(key='admin_email').first()
            if not setting or not setting.value:
                print("[EmailService] No admin_email configured", flush=True)
                return False

            admin_email = setting.value
            subject = "HaresNet - Login Verification Code"
            
            # Plain text fallback
            body_text = f"Hello Admin,\n\nYour login verification code is: {otp_code}\n\nThis code expires in 60 seconds.\n\nRegards,\nHaresNet System"
            
            # HTML version
            body_html = self._load_template('email_otp.html', otp_code=otp_code)

            return self.send_email(admin_email, subject, body_text, body_html)
        except Exception as e:
            print(f"[EmailService] Error in send_otp: {str(e)}", flush=True)
            return False

    def send_password_reset(self, email, reset_code):
        """Send password reset code with HTML template"""
        try:
            subject = "HaresNet - Password Reset Code"
            
            # Plain text fallback
            body_text = f"Hello Admin,\n\nYour password reset code is: {reset_code}\n\nThis code expires in 10 minutes.\n\nIf you didn't request this, please ignore this email.\n\nRegards,\nHaresNet System"
            
            # HTML version
            body_html = self._load_template('email_reset_password.html', reset_code=reset_code)

            return self.send_email(email, subject, body_text, body_html)
        except Exception as e:
            print(f"[EmailService] Error in send_password_reset: {str(e)}", flush=True)
            return False
