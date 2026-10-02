"""HTTP server for the web interface

    GET  /api/state    full state (devices, effects, options, profiles, audio)
    POST /api/action   {"action": "set-effect", "payload": {...}}
    GET  /api/events   server-sent events:
                         state  the full state, sent on connect and on change
                         frame  latest LED bytes per device (base64, what was
                                sent to each ESP) plus the music features
                                (spectrum, band meters, tempo, beat count)
    GET  /*            the built web interface from ../web/dist
"""
import base64
import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import lib.api as api

WEB_DIST = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "web", "dist")
CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".ico": "image/x-icon",
    ".json": "application/json",
}
FRAME_RATE = 60


class Broadcaster:
    """Tracks state changes and the latest music features for the event stream"""
    def __init__(self):
        self.state_version = 0
        self.spectrum = []
        self.meters = {}
        self.tempo = 0.0
        self.position = None
        # A running count rather than a flag, so the page can't miss a beat between events
        self.beats = 0
        self._changed = threading.Condition()
        api.on_change(self.state_changed)

    def state_changed(self):
        with self._changed:
            self.state_version += 1
            self._changed.notify_all()

    def set_features(self, features):
        self.spectrum = [round(float(v), 3) for v in features.bins]
        self.meters = {name: round(getattr(features, name), 3) for name in ("bass", "mid", "treble", "intensity")}
        self.tempo = round(features.tempo, 1)
        # Seconds into a pre-analysed track, for the track map's playhead
        self.position = None if features.position is None else round(features.position, 2)
        self.beats += features.beat


broadcaster = Broadcaster()


def _event(name, data):
    return "event: {}\ndata: {}\n\n".format(name, data).encode()


def make_handler(boards):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def _send(self, status, body, content_type):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _json(self, data, status=200):
            self._send(status, api.to_json(data).encode(), "application/json")

        def do_GET(self):
            path = self.path.split("?")[0]
            if path == "/api/state":
                return self._json(api.get_state())
            if path == "/api/events":
                return self._events()
            return self._static(path)

        def do_POST(self):
            if self.path != "/api/action":
                return self._json({"error": "Not found"}, 404)
            try:
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            except ValueError:
                return self._json({"error": "Invalid JSON"}, 400)
            error = api.run_action(body.get("action"), body.get("payload", {}))
            if error:
                return self._json({"error": error}, 400)
            self._json({"ok": True})

        def _static(self, path):
            if not os.path.isdir(WEB_DIST):
                return self._send(404, b"Web interface not built. Run: cd web && npm install && npm run build\n",
                                  "text/plain")
            file_path = os.path.normpath(os.path.join(WEB_DIST, path.lstrip("/")))
            if not file_path.startswith(WEB_DIST):
                return self._send(404, b"Not found", "text/plain")
            if not os.path.isfile(file_path):
                # Single page app: unknown paths get the index
                file_path = os.path.join(WEB_DIST, "index.html")
            content_type = CONTENT_TYPES.get(os.path.splitext(file_path)[1], "application/octet-stream")
            with open(file_path, "rb") as f:
                self._send(200, f.read(), content_type)

        def _events(self):
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            sent_version = None
            sent_frames = {}
            try:
                while True:
                    if sent_version != broadcaster.state_version:
                        sent_version = broadcaster.state_version
                        self.wfile.write(_event("state", api.to_json(api.get_state())))

                    leds = {}
                    for name, board in boards.items():
                        esp = board.esp
                        if sent_frames.get(name) != esp.frame_count:
                            sent_frames[name] = esp.frame_count
                            leds[name] = base64.b64encode(esp.last_frame).decode()
                    if leds:
                        self.wfile.write(_event("frame", json.dumps({
                            "leds": leds,
                            "spectrum": broadcaster.spectrum,
                            "meters": broadcaster.meters,
                            "tempo": broadcaster.tempo,
                            "beats": broadcaster.beats,
                            "position": broadcaster.position,
                        })))
                    self.wfile.flush()
                    time.sleep(1.0 / FRAME_RATE)
            except (BrokenPipeError, ConnectionResetError):
                pass

    return Handler


def start(boards, host, port):
    server = ThreadingHTTPServer((host, port), make_handler(boards))
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server
