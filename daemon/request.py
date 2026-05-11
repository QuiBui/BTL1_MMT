#
# Copyright (C) 2026 pdnguyen of HCMC University of Technology VNU-HCM.
# All rights reserved.
# This file is part of the CO3093/CO3094 course.
#
# AsynapRous release
#
# The authors hereby grant to Licensee personal permission to use
# and modify the Licensed Source Code for the sole purpose of studying
# while attending the course
#

"""
daemon.request
~~~~~~~~~~~~~~~~~

This module provides a Request object to manage and persist 
request settings (cookies, auth, proxies).
"""
from .dictionary import CaseInsensitiveDict

class Request():
    """The fully mutable "class" `Request <Request>` object,
    containing the exact bytes that will be sent to the server.

    Instances are generated from a "class" `Request <Request>` object, and
    should not be instantiated manually; doing so may produce undesirable
    effects.
    """
    __attrs__ = [
        "method",
        "url",
        "headers",
        "body",
        "_raw_headers",
        "_raw_body",
        "reason",
        "cookies",
        "routes",
        "hook",
    ]

    def __init__(self):
        #: HTTP verb to send to the server.
        self.method = None
        #: HTTP URL to send the request to.
        self.url = None
        #: dictionary of HTTP headers.
        self.headers = CaseInsensitiveDict()
        #: HTTP path
        self.path = None        
        # The cookies set used to create Cookie header
        self.cookies = {}
        #: request body to send to the server.
        self.body = ""
        # The raw header
        self._raw_headers = ""
        #: The raw body
        self._raw_body = ""
        #: Routes
        self.routes = {}
        #: Hook point for routed mapped-path
        self.hook = None

    def extract_request_line(self, request):
        try:
            lines = request.splitlines()
            if not lines:
                return None, None, None
                
            first_line = lines[0]
            parts = first_line.split()
            
            if len(parts) == 3:
                method, path, version = parts
            elif len(parts) == 2:
                method, path = parts
                version = "HTTP/1.1"
            else:
                return None, None, None

            if path == '/':
                path = '/index.html'
                
            return method, path, version
        except Exception:
            return None, None, None
             
    def prepare_headers(self, raw_headers):
        """Prepares the given HTTP headers."""
        lines = raw_headers.split('\r\n')
        headers = CaseInsensitiveDict()
        for line in lines[1:]:
            if line.strip() == '':
                break # End of headers
            if ': ' in line:
                key, val = line.split(': ', 1)
                headers[key.lower()] = val.strip()
        return headers

    def fetch_headers_body(self, request):
        """Prepares the given HTTP headers."""
        # Split request into header section and body section
        parts = request.split("\r\n\r\n", 1)  # split once at blank line

        _headers = parts[0]
        _body = parts[1] if len(parts) > 1 else ""
        return _headers, _body

    def prepare(self, request, routes=None):
        """Prepares the entire request with the given parameters."""

        print("[Request] prepare request msg:\n {}".format(request))
        self.method, self.path, self.version = self.extract_request_line(request)
        if not self.method: 
            return
        
        print("[Request] {} path {} version {}".format(self.method, self.path, self.version))
        
        self._raw_headers, self._raw_body = self.fetch_headers_body(request)
        self.headers = self.prepare_headers(self._raw_headers)
        self.body = self._raw_body

        # Parse Cookies from headers properly
        cookie_header = self.headers.get('cookie', '')
        self.cookies = {}
        if cookie_header:
            for pair in cookie_header.split(';'):
                if '=' in pair:
                    k, v = pair.strip().split('=', 1)
                    self.cookies[k] = v

        # Prepare hook mapping
        if routes is not None and routes != {}:
            self.routes = routes
            print("[Request] Routing METHOD {} path {}".format(self.method, self.path))
            self.hook = routes.get((self.method, self.path))
            if self.hook:
                print("[Request] Hook mapped successfully for path: {}".format(self.path))

        return

    def prepare_body(self, data, files=None, json=None):
        self.body = data
        self.prepare_content_length(data)
        return

    def prepare_content_length(self, body):
        """Calculate exact length of body to prevent truncation in data streams"""
        if body is not None:
            length = len(body.encode('utf-8'))
            self.headers["content-length"] = str(length)
        else:
            self.headers["content-length"] = "0"
        return

    def prepare_auth(self, auth, url=""):
        # Not used in this assignment since we manage auth via Cookies
        pass

    def prepare_cookies(self, cookies):
        if isinstance(cookies, dict):
            cookie_str = "; ".join([f"{k}={v}" for k, v in cookies.items()])
            self.headers["cookie"] = cookie_str
        elif isinstance(cookies, str):
            self.headers["cookie"] = cookies