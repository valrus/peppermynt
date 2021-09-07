# -*- coding: utf-8 -*-

from http.server import SimpleHTTPRequestHandler
from socketserver import TCPServer

from peppermynt.utils import get_logger


logger = get_logger('peppermynt')


class RequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, request, client_address, base_url, server):
        self.base_url = base_url

        SimpleHTTPRequestHandler.__init__(self, request, client_address, server)

    def do_GET(self):
        self.path = self.path.replace(self.base_url, '/')

        SimpleHTTPRequestHandler.do_GET(self)


class Server(TCPServer):
    allow_reuse_address = True

    def __init__(self, server_address, base_url, RequestHandlerClass, bind_and_activate = True):
        TCPServer.__init__(self, server_address, RequestHandlerClass, bind_and_activate)

        self.base_url = base_url

    def finish_request(self, request, client_address):
        self.RequestHandlerClass(request, client_address, self.base_url, self)
