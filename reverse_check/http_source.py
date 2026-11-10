"""Bounded public GETs with checked redirects and pinned DNS answers."""

from dataclasses import dataclass
import http.client
import ipaddress
import math
import socket
import ssl
import time
import threading
from urllib.parse import quote, urljoin, urlsplit, urlunsplit


@dataclass(frozen=True)
class FetchedPage:
    final_url: str
    status_code: int
    content_type: str
    body: bytes


class FetchError(Exception):
    def __init__(self,status,detail,http_status=None,final_url=None):
        super().__init__(detail)
        self.status=status;self.http_status=http_status;self.final_url=final_url


def parse_url(url):
    try:
        if not isinstance(url,str) or any(c.isspace() or ord(c)<32 for c in url):raise ValueError()
        parts=urlsplit(url)
        if parts.scheme not in {'http','https'} or not parts.hostname or parts.username is not None or parts.password is not None:raise ValueError()
        _=parts.port
        host=parts.hostname.encode('idna').decode('ascii').rstrip('.')
        if '%' in host or '\\' in host:raise ValueError()
        return parts,host
    except (ValueError,UnicodeError) as exc:
        raise FetchError('unsafe_url','只接受不含凭据或控制字符的HTTP(S) URL') from exc


def _addresses(host,port):
    try:
        literal=ipaddress.ip_address(host)
    except ValueError:literal=None
    if literal and not literal.is_global:raise FetchError('unsafe_url','拒绝访问非公网地址')
    answers=socket.getaddrinfo(host,port,type=socket.SOCK_STREAM)
    ips=[]
    for _,_,_,_,address in answers:
        ip=ipaddress.ip_address(address[0])
        if not ip.is_global:raise FetchError('unsafe_url','DNS答案包含非公网地址')
        if str(ip) not in ips:ips.append(str(ip))
    if not ips:raise OSError('DNS没有返回可用地址')
    return ips


def public_fetch(url,timeout=10,max_bytes=1000000,allow_url=None):
    if isinstance(timeout,bool) or not isinstance(timeout,(int,float)) or not math.isfinite(timeout) or not 0<timeout<=120:
        raise ValueError('timeout需要大于0且不超过120秒')
    if type(max_bytes) is not int or not 1<=max_bytes<=10000000:raise ValueError('max_bytes需要1–10000000')
    deadline=time.monotonic()+timeout
    current=url;received_status=None
    def remaining():
        left=deadline-time.monotonic()
        if left<=0:raise FetchError('timeout','连接或读取超时',http_status=received_status,final_url=current)
        return left
    try:
        for hop in range(6):
            received_status=None
            parts,host=parse_url(current)
            if allow_url is not None:allow_url(current)
            port=parts.port or (443 if parts.scheme=='https' else 80)
            addresses=_addresses(host,port)
            connection=http.client.HTTPConnection(host,port,timeout=remaining())
            raw_socket=None;response=None;watchdog=None;expired=threading.Event()
            try:
                last_error=None
                for address in addresses:
                    try:
                        raw_socket=socket.create_connection((address,port),timeout=remaining())
                        break
                    except OSError as exc:last_error=exc
                if raw_socket is None:raise last_error or OSError('无法连接')
                raw_socket.settimeout(remaining())
                if parts.scheme=='https':
                    raw_socket=ssl.create_default_context().wrap_socket(raw_socket,server_hostname=host)
                def expire_socket(sock=raw_socket,expired=expired):
                    expired.set()
                    try:sock.shutdown(socket.SHUT_RDWR)
                    except OSError:pass
                watchdog=threading.Timer(remaining(),expire_socket)
                watchdog.daemon=True;watchdog.start()
                connection.sock=raw_socket
                raw_socket.settimeout(remaining())
                path=quote(parts.path or '/',safe="/%:@!$&'()*+,;=-._~")
                query=quote(parts.query,safe="=&?/%:@!$'()*+,;~-._")
                target=urlunsplit(('','',path,query,''))
                connection.request('GET',target,headers={'User-Agent':'reverse-check/0.2 public-source-collector','Accept':'text/html, text/plain, application/xhtml+xml','Accept-Encoding':'identity','Connection':'close'})
                raw_socket.settimeout(remaining())
                response=connection.getresponse()
                received_status=response.status
                if response.status in {301,302,303,307,308} and response.getheader('Location'):
                    next_url=urljoin(current,response.getheader('Location'))
                    if hop==5:raise FetchError('redirect_limit','重定向超过5次',response.status,current)
                    current=next_url
                    continue
                encoding=response.getheader('Content-Encoding','identity').strip().lower()
                if encoding not in {'','identity'}:raise FetchError('unsupported_content','服务器返回压缩正文，未解压',response.status,current)
                declared=response.getheader('Content-Length')
                if declared and declared.isdigit() and int(declared)>max_bytes:
                    raise FetchError('too_large','正文超过大小上限',response.status,current)
                chunks=[];size=0
                while not response.isclosed():
                    raw_socket.settimeout(remaining())
                    chunk=response.read1(min(65536,max_bytes-size+1))
                    if not chunk:break
                    chunks.append(chunk);size+=len(chunk)
                    if size>max_bytes:raise FetchError('too_large','正文超过大小上限',response.status,current)
                if expired.is_set():raise FetchError('timeout','连接或读取超时',received_status,current)
                remaining()
                if response.length not in (None,0):
                    raise FetchError('network_error','正文在声明长度之前截断',response.status,current)
                return FetchedPage(current,response.status,response.getheader('Content-Type',''),b''.join(chunks))
            finally:
                if watchdog is not None:watchdog.cancel()
                if response is not None:response.close()
                connection.close()
                if raw_socket is not None:raw_socket.close()
    except FetchError:raise
    except (socket.timeout,TimeoutError) as exc:raise FetchError('timeout','连接或读取超时',http_status=received_status,final_url=current) from exc
    except (OSError,http.client.HTTPException,ValueError) as exc:
        if time.monotonic()>=deadline:raise FetchError('timeout','连接或读取超时',http_status=received_status,final_url=current) from exc
        raise FetchError('network_error',str(exc)[:400],http_status=received_status,final_url=current) from exc
    raise FetchError('redirect_limit','重定向次数超限',final_url=current)
