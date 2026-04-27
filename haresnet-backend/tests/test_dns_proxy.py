import unittest
import socket
import threading
import time
from unittest.mock import MagicMock, patch
from app.services.dns_proxy import DNSProxyService
from app.models import DomainFilter

class TestDNSProxy(unittest.TestCase):
    def setUp(self):
        self.proxy = DNSProxyService(host='127.0.0.1', port=5053, upstream_host='127.0.0.1', upstream_port=5353)
        self.proxy.app = MagicMock()
        self.proxy.app.app_context.return_value = MagicMock()
        self.proxy.app.app_context.return_value.__enter__.return_value = None
        self.proxy.app.app_context.return_value.__exit__.return_value = None
        
        # Mock DNS Manager
        self.proxy.dns_manager = MagicMock()
        self.proxy.dns_manager.match_domain_against_filters.return_value = (False, None)

    def test_parse_dns_packet(self):
        # Construct a simple query packet for google.com (Type A)
        # Header: ID=0x1234, Flags=0x0100 (Standard Query), QDCOUNT=1, others=0
        header = b'\x12\x34\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00'
        # Question: 6google3com0 (0x00) + Type A (0x0001) + Class IN (0x0001)
        question = b'\x06google\x03com\x00\x00\x01\x00\x01'
        packet = header + question
        
        domain, qtype = self.proxy._parse_dns_packet(packet)
        self.assertEqual(domain, 'google.com')
        self.assertEqual(qtype, 1)

    @patch('socket.socket')
    def test_forward_query(self, mock_socket):
        mock_sock_instance = MagicMock()
        mock_socket.return_value = mock_sock_instance
        mock_sock_instance.recvfrom.return_value = (b'response', ('127.0.0.1', 5353))
        
        response = self.proxy._forward_query(b'query')
        
        mock_sock_instance.sendto.assert_called_with(b'query', ('127.0.0.1', 5353))
        self.assertEqual(response, b'response')

    def test_dns_filtering_integration(self):
        # Mock filter match
        self.proxy.dns_manager.match_domain_against_filters.return_value = (True, MagicMock(id=1, name='TestFilter'))
        
        # We need to simulate the _handle_request method but we'll just check logic here
        # Construct packet
        header = b'\x12\x34\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00'
        # badad is 5 chars, so \x05
        question = b'\x05badad\x03com\x00\x00\x01\x00\x01'
        packet = header + question
        
        # Inject socket
        self.proxy.sock = MagicMock()
        
        # Run handle request
        self.proxy._handle_request(packet, ('127.0.0.1', 12345))
        
        # Should NOT forward (upstream socket not created)
        # Should send blocked response
        self.proxy.sock.sendto.assert_called()
        # Verify log called
        self.proxy.dns_manager.log_dns_query.assert_called()
        call_args = self.proxy.dns_manager.log_dns_query.call_args[1]
        self.assertEqual(call_args['was_blocked'], True)
        self.assertEqual(call_args['query_domain'], 'badad.com')

if __name__ == '__main__':
    unittest.main()
