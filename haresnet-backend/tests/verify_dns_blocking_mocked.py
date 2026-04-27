
import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# 1. MOCK DEPENDENCIES in sys.modules
mock_flask = MagicMock()
mock_sqlalchemy_ext = MagicMock() # flask_sqlalchemy
mock_sqlalchemy_core = MagicMock() # sqlalchemy
mock_cors = MagicMock()
mock_jwt = MagicMock()
mock_socketio = MagicMock()
mock_bcrypt = MagicMock()
mock_eventlet = MagicMock()
mock_watchdog_observers = MagicMock()
mock_watchdog_events = MagicMock()

sys.modules['flask'] = mock_flask
sys.modules['flask_sqlalchemy'] = mock_sqlalchemy_ext
sys.modules['sqlalchemy'] = mock_sqlalchemy_core
# Mock submodules of sqlalchemy that might be imported
sys.modules['sqlalchemy.orm'] = MagicMock()
sys.modules['sqlalchemy.ext'] = MagicMock()
sys.modules['sqlalchemy.sql'] = MagicMock()

sys.modules['flask_cors'] = mock_cors
sys.modules['flask_jwt_extended'] = mock_jwt
sys.modules['flask_socketio'] = mock_socketio
sys.modules['bcrypt'] = mock_bcrypt
sys.modules['eventlet'] = mock_eventlet
sys.modules['watchdog'] = MagicMock()
sys.modules['watchdog.observers'] = mock_watchdog_observers
sys.modules['watchdog.events'] = mock_watchdog_events
sys.modules['config'] = MagicMock()

# Add project root
sys.path.append(os.getcwd())

from app.services.dns_filter_manager import DNSFilterManager
from app.services.dns_proxy import DNSProxyService
from app.models import DomainFilter

class TestDNSBlockingRefined(unittest.TestCase):
    def setUp(self):
        self.manager = DNSFilterManager()
        
    def test_regex_matching_logic(self):
        # We assume DomainFilter is a valid class or mock
        # If it inherits from Mock, we can instantiate it
        
        regex_filter = DomainFilter()
        regex_filter.pattern_type = 'regex'
        regex_filter.regex_pattern = r"face.*book"
        regex_filter.domain = "regex_test"
        
        # Test matching
        match = self.manager._domain_matches_filter("facebook.com", regex_filter)
        print(f"Match 'facebook.com' against 'face.*book': {match}")
        self.assertTrue(match)
        
        match = self.manager._domain_matches_filter("google.com", regex_filter)
        print(f"Match 'google.com' against 'face.*book': {match}")
        self.assertFalse(match)
        
        # Test case insensitive
        regex_filter.regex_pattern = r"BadSite"
        match = self.manager._domain_matches_filter("badsite.com", regex_filter)
        print(f"Match 'badsite.com' against 'BadSite': {match}")
        self.assertTrue(match)

    @patch('requests.post')
    @patch('app.services.dns_proxy.DNSProxyService._get_client_info')
    def test_notification(self, mock_get_client_info, mock_post):
        # Patch create_app WHERE IT IS USED
        with patch('app.services.dns_proxy.create_app', return_value=MagicMock()):
             proxy = DNSProxyService()
        
        proxy.app = MagicMock() 
        
        # Mock client info return
        mock_get_client_info.return_value = ("AA:BB:CC:DD:EE:FF", "Mock Device")
        
        # Mock filter
        mock_filter = MagicMock()
        mock_filter.group.name = "Ads Blocklist"
        
        # Trigger notification
        proxy._send_blocking_notification("10.0.0.5", "ads.google.com", mock_filter)
        
        # Verify
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        data = kwargs.get('data', '')
        
        print(f"Notification Sent: {data}")
        
        self.assertIn("Blocked access to ads.google.com", data)
        self.assertIn("10.0.0.5", data)
        self.assertIn("AA:BB:CC:DD:EE:FF", data)
        self.assertIn("Ads Blocklist", data)

if __name__ == '__main__':
    unittest.main()
