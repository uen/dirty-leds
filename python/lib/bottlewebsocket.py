import logging
from lib.bottle import ServerAdapter, request

from gevent import pywsgi
from geventwebsocket.handler import WebSocketHandler
from geventwebsocket.logging import create_logger



class GeventWebSocketServer(ServerAdapter):
    def run(self, handler):
        server = pywsgi.WSGIServer((self.host, self.port), handler, handler_class=WebSocketHandler)

        server.serve_forever()

def websocket(callback):
    def wrapper(*args, **kwargs):

        callback(request.environ.get('wsgi.websocket'), *args, **kwargs)

    return wrapper

