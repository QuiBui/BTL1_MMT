#
# Copyright (C) 2026 pdnguyen of HCMC University of Technology VNU-HCM.
# All rights reserved.
# This file is part of the CO3093/CO3094 course.
#
# AsynApRous release
#
# The authors hereby grant to Licensee personal permission to use
# and modify the Licensed Source Code for the sole purpose of studying
# while attending the course
#

"""
daemon.response
~~~~~~~~~~~~~~~~~

This module provides a :class: `Response <Response>` object to manage and persist 
response settings (cookies, auth, proxies), and to construct HTTP responses
based on incoming requests. 

The current version supports MIME type detection, content loading and header formatting
"""
import datetime
import os
import mimetypes
from .dictionary import CaseInsensitiveDict

BASE_DIR = ""

class Response():   
    """The :class:`Response <Response>` object, which contains a
    server's response to an HTTP request.
    """

    __attrs__ = [
        "_content",
        "_header",
        "status_code",
        "method",
        "headers",
        "url",
        "history",
        "encoding",
        "reason",
        "cookies",
        "elapsed",
        "request",
        "body",
        "reason",
    ]


    def __init__(self, request=None):
        """
        Initializes a new :class:`Response <Response>` object.
        """
        self._content = b""
        self._content_consumed = False
        self._next = None

        self.status_code = 200
        self.headers = CaseInsensitiveDict()
        self.url = None
        self.encoding = None
        self.history = []
        self.reason = None
        
        # Dictionary lưu các cookie sẽ được set (Set-Cookie)
        self.cookies = {}
        self.elapsed = datetime.timedelta(0)
        self.request = request

    def get_mime_type(self, path):
        """Determines the MIME type of a file based on its path."""
        try:
            mime_type, _ = mimetypes.guess_type(path)
        except Exception:
            return 'application/octet-stream'
        return mime_type or 'application/octet-stream'

    def prepare_content_type(self, mime_type='text/html'):
        """
        Prepares the Content-Type header and determines the base directory
        for serving the file based on its MIME type.
        """
        base_dir = BASE_DIR + "static/" # Default fallback
        self.headers['Content-Type'] = mime_type
        
        # Tránh lỗi nếu mime_type không có dấu '/'
        if '/' not in mime_type:
            return base_dir

        main_type, sub_type = mime_type.split('/', 1)
        print("[Response] Processing main_type={} sub_type={}".format(main_type, sub_type))
        
        if mime_type == 'text/html':
            base_dir = BASE_DIR + "www/"
        elif main_type == 'text' or main_type == 'image':
            base_dir = BASE_DIR + "static/"
        elif mime_type == 'application/json':
            base_dir = "" # API trả dữ liệu trực tiếp, không cần base_dir
        elif main_type == 'application':
            # Hỗ trợ file javascript
            if sub_type in ['javascript', 'x-javascript']:
                base_dir = BASE_DIR + "static/"
            else:
                base_dir = BASE_DIR + "apps/"
                
        return base_dir

    def build_content(self, path, base_dir):
        """Loads the objects file from storage space."""
        filepath = os.path.join(base_dir, path.lstrip('/'))
        print("[Response] Serving the object at location {}".format(filepath))
        
        try:
            with open(filepath, "rb") as f:
               content = f.read()
        except Exception as e:
            print("[Response] build_content exception: {}".format(e))
            return -1, b""
        return len(content), content

    def build_response_header(self, request):
        # Các header bắt buộc
        headers_dict = {
            "Content-Type": self.headers.get('Content-Type', 'text/plain'),
            "Content-Length": str(len(self._content) if self._content else 0),
            "Connection": "close",
            "Date": datetime.datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT"),
            "Server": "AsynapRous/1.0",
            "Access-Control-Allow-Origin": "*"
        }

        # Định dạng Header HTTP thành chuỗi
        header_str = "HTTP/1.1 200 OK\r\n"
        for key, value in headers_dict.items():
            header_str += "{}: {}\r\n".format(key, value)

        # Xử lý việc chèn nhiều Cookie động được trả về từ lớp App (RFC 6265)
        for key, value in self.cookies.items():
            if "Path=" not in str(value):
                header_str += "Set-Cookie: {}={}; Path=/; HttpOnly\r\n".format(key, value)
            else:
                header_str += "Set-Cookie: {}={}\r\n".format(key, value)

        header_str += "\r\n" # Dòng trống phân cách Header và Body
        return header_str.encode('utf-8')

    def build_notfound(self):
        """Constructs a standard 404 Not Found HTTP response."""
        return (
                "HTTP/1.1 404 Not Found\r\n"
                "Accept-Ranges: bytes\r\n"
                "Content-Type: text/html\r\n"
                "Content-Length: 13\r\n"
                "Connection: close\r\n"
                "\r\n"
                "404 Not Found"
            ).encode('utf-8')

    def build_response(self, request, envelop_content=None):
        """
        Builds a full HTTP response including headers and content based on the request.
        """
        print("[Response] Start build response with req path: {}".format(request.path))

        path = request.path
        mime_type = self.get_mime_type(path)
        print("[Response] {} path {} mime_type {}".format(request.method, request.path, mime_type))

        base_dir = ""
        # Nếu có nội dung trả về từ tầng WebApp (API hook)
        if envelop_content is not None:
            self.prepare_content_type('application/json')
            
            # Hỗ trợ WebApp trả về tuple: (content_bytes, dict_cookies)
            if isinstance(envelop_content, tuple) and len(envelop_content) == 2:
                content_body, new_cookies = envelop_content
                self._content = content_body
                if isinstance(new_cookies, dict):
                    for k, v in new_cookies.items():
                        self.cookies[k] = v
            else:
                self._content = envelop_content
                
            # Đảm bảo nội dung là bytes
            if isinstance(self._content, str):
                self._content = self._content.encode('utf-8')
                
        # Ngược lại, nạp nội dung file tĩnh (HTML, CSS, JS, PNG...)
        else:
            if path == '/' or path.endswith('.html'):
                base_dir = self.prepare_content_type('text/html')
            elif mime_type == 'text/css':
                base_dir = self.prepare_content_type('text/css')
            elif mime_type.startswith('image/') or mime_type in ['application/javascript', 'text/javascript']:
                base_dir = self.prepare_content_type(mime_type)
            else:
                return self.build_notfound()

            length, self._content = self.build_content(path, base_dir)
            if length == -1: 
                return self.build_notfound()

        self._header = self.build_response_header(request)
        return self._header + self._content