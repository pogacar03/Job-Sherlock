from contextlib import contextmanager
import http.client
import socket
import threading
import time
import unittest
from unittest.mock import patch

from reverse_check.http_source import FetchError, public_fetch


PUBLIC_DNS=[(socket.AF_INET,socket.SOCK_STREAM,6,'',('93.184.216.34',80))]


@contextmanager
def wire(responses, dns=None):
    """Real HTTP over paired sockets; only DNS/connect side effects are replaced."""
    peers=[]
    requests=[]
    addresses=[]
    def connect(address, timeout=None):
        addresses.append(address)
        payload=responses[len(addresses)-1]
        client,server=socket.socketpair()
        client.settimeout(timeout)
        def serve():
            try:
                request=b''
                while b'\r\n\r\n' not in request:
                    chunk=server.recv(4096)
                    if not chunk:break
                    request+=chunk
                requests.append(request)
                if callable(payload):payload(server)
                else:server.sendall(payload)
            except (BrokenPipeError,ConnectionResetError):pass
            finally:server.close()
        thread=threading.Thread(target=serve,daemon=True);thread.start();peers.append(thread)
        return client
    with patch('reverse_check.http_source.socket.getaddrinfo',side_effect=dns if callable(dns) else None,return_value=dns or PUBLIC_DNS),patch('reverse_check.http_source.socket.create_connection',side_effect=connect):
        yield requests,addresses
    for thread in peers:thread.join(timeout=1)


class HttpSourceTests(unittest.TestCase):
    def test_fetch_reads_real_http_and_pins_connection_to_public_dns_answer(self):
        with wire([b'HTTP/1.1 200 OK\r\nContent-Type: text/plain; charset=utf-8\r\nContent-Length: 5\r\nConnection: close\r\n\r\nhello']) as (requests,addresses):
            page=public_fetch('http://example.com/article',timeout=2,max_bytes=100)
        self.assertEqual(page.body,b'hello')
        self.assertEqual(page.status_code,200)
        self.assertEqual(addresses,[('93.184.216.34',80)])
        self.assertIn(b'GET /article HTTP/1.1',requests[0])
        self.assertIn(b'Host: example.com',requests[0])

    def test_rejects_credentials_private_dns_and_mixed_dns_before_connect(self):
        private=[(socket.AF_INET,socket.SOCK_STREAM,6,'',('127.0.0.1',80))]
        for url,answers in [('http://user:pass@example.com',PUBLIC_DNS),('http://example.com',private),('http://example.com',PUBLIC_DNS+private),('file:///etc/passwd',PUBLIC_DNS)]:
            with self.subTest(url=url,answers=answers),wire([],dns=answers) as (_,addresses):
                with self.assertRaises(FetchError) as error:public_fetch(url,2,100)
                self.assertEqual(error.exception.status,'unsafe_url')
                self.assertEqual(addresses,[])

    def test_redirect_into_private_network_is_blocked_before_second_request(self):
        response=b'HTTP/1.1 302 Found\r\nLocation: http://127.0.0.1/secret\r\nContent-Length: 0\r\nConnection: close\r\n\r\n'
        with wire([response]) as (_,addresses):
            with self.assertRaises(FetchError) as error:public_fetch('http://example.com/a',2,100)
        self.assertEqual(error.exception.status,'unsafe_url')
        self.assertEqual(len(addresses),1)

    def test_declared_oversized_body_is_rejected(self):
        response=b'HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nContent-Length: 9999\r\nConnection: close\r\n\r\n'
        with wire([response]):
            with self.assertRaises(FetchError) as error:public_fetch('http://example.com/a',2,100)
        self.assertEqual(error.exception.status,'too_large')

    def test_redirect_preserves_final_url_and_cannot_loop_forever(self):
        redirect=b'HTTP/1.1 302 Found\r\nLocation: /next\r\nContent-Length: 0\r\nConnection: close\r\n\r\n'
        success=b'HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nContent-Length: 2\r\nConnection: close\r\n\r\nok'
        with wire([redirect,success]):
            self.assertEqual(public_fetch('http://example.com/a',2,100).final_url,'http://example.com/next')
        with wire([redirect]*6):
            with self.assertRaises(FetchError) as error:public_fetch('http://example.com/a',2,100)
        self.assertEqual(error.exception.status,'redirect_limit')

    def test_truncated_body_is_not_returned_as_complete_original(self):
        response=b'HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nContent-Length: 20\r\nConnection: close\r\n\r\nshort'
        with wire([response]):
            with self.assertRaises(FetchError) as error:public_fetch('http://example.com/a',2,100)
        self.assertEqual(error.exception.status,'network_error')

    def test_redirect_source_policy_is_checked_before_following(self):
        redirect=b'HTTP/1.1 302 Found\r\nLocation: http://manual.example/private\r\nContent-Length: 0\r\nConnection: close\r\n\r\n'
        def policy(url):
            if 'manual.example' in url:raise FetchError('manual_required','manual source')
        with wire([redirect]) as (_,addresses):
            with self.assertRaises(FetchError) as error:public_fetch('http://example.com/a',2,100,allow_url=policy)
        self.assertEqual(error.exception.status,'manual_required')
        self.assertEqual(len(addresses),1)

    def test_slow_drip_headers_cannot_extend_the_request_budget(self):
        def slow(server):
            for byte in b'HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nContent-Length: 2\r\n\r\nok':
                server.sendall(bytes([byte]));threading.Event().wait(.02)
        start=time.monotonic()
        with wire([slow]):
            with self.assertRaises(FetchError) as error:public_fetch('http://example.com/a',.1,100)
        self.assertEqual(error.exception.status,'timeout')
        self.assertLess(time.monotonic()-start,.6)

    def test_timeout_without_content_length_cannot_return_a_truncated_success(self):
        def slow(server):
            server.sendall(b'HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nConnection: close\r\n\r\nA public article with more than thirty characters. ')
            for _ in range(30):
                server.sendall(b'more ');threading.Event().wait(.02)
        with wire([slow]):
            with self.assertRaises(FetchError) as error:public_fetch('http://example.com/a',.12,1000)
        self.assertEqual(error.exception.status,'timeout')

    def test_eof_after_budget_is_not_success_even_without_length_header(self):
        clock={'now':100.0}
        original=http.client.HTTPResponse.read1
        def read1(response,n=-1):
            data=original(response,n)
            if not data:clock['now']=101.0
            return data
        payload=b'HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nConnection: close\r\n\r\nAn article with enough text to create a readable draft.'
        with wire([payload]),patch('reverse_check.http_source.time.monotonic',side_effect=lambda:clock['now']),patch('http.client.HTTPResponse.read1',read1):
            with self.assertRaises(FetchError) as error:public_fetch('http://example.com/a',.5,1000)
        self.assertEqual(error.exception.status,'timeout')

    def test_body_timeout_keeps_known_http_status(self):
        for code in [403,429,503]:
            payload=f'HTTP/1.1 {code} Error\r\nContent-Type: text/plain\r\nContent-Length: 1000\r\nConnection: close\r\n\r\n'.encode()
            with self.subTest(code=code),wire([payload]),patch('http.client.HTTPResponse.read1',side_effect=TimeoutError('read timeout')):
                with self.assertRaises(FetchError) as error:public_fetch('http://example.com/a',2,2000)
                self.assertEqual(error.exception.status,'timeout')
                self.assertEqual(error.exception.http_status,code)
