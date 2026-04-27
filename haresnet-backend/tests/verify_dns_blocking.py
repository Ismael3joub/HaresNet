
import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from app.services.dns_filter_manager import DNSFilterManager
from app.models import DomainFilter, DomainFilterGroup

class TestDNSBlocking(unittest.TestCase):
    def setUp(self):
        self.manager = DNSFilterManager()
        
    def test_regex_matching(self):
        # Create a mock filter for regex
        regex_filter = DomainFilter(
            domain="Regex Match",
            pattern_type='regex',
            regex_pattern=r"face.*book",
            enabled=True,
            blocking_enabled=True
        )
        
        # Test matching
        self.assertTrue(self.manager._domain_matches_filter("facebook.com", regex_filter))
        self.assertTrue(self.manager._domain_matches_filter("m.facebook.com", regex_filter))
        self.assertTrue(self.manager._domain_matches_filter("sub.facebook-login.com", regex_filter))
        self.assertFalse(self.manager._domain_matches_filter("google.com", regex_filter))
        
        print("Regex matching verification passed.")

    @patch('requests.post')
    @patch('app.services.dns_proxy.DNSProxyService._get_client_info')
    def test_notification(self, mock_get_client_info, mock_post):
        from app.services.dns_proxy import DNSProxyService
        
        # Mock dependencies
        proxy = DNSProxyService()
        proxy.app = MagicMock() # Mock flask app
        
        # Mock client info
        mock_get_client_info.return_value = ("00:11:22:33:44:55", "Test Device")
        
        # Mock filter
        mock_filter = MagicMock()
        mock_filter.group.name = "Test Blocklist"
        
        # Call the notification method
        proxy._send_blocking_notification("192.168.1.100", "badsite.com", mock_filter)
        
        # Assert requests.post was called with correct data
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertIn("Blocked access to badsite.com", kwargs['data'])
        self.assertIn("192.168.1.100", kwargs['data'])
        self.assertIn("00:11:22:33:44:55", kwargs['data'])
        self.assertIn("Test Blocklist", kwargs['data'])
        
        print("Notification logic verification passed.")

if __name__ == '__main__':
    unittest.main()
