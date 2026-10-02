"""Audio input

AudioInput feeds the callback one frame of mono int16 samples (as float32),
MIC_RATE / FPS samples at a time, from a source that can be switched while
running:

    off            silence, so non-reactive effects keep animating
    mic            default input device (pyaudio)
    system         whatever is playing on this machine (PipeWire sink monitor)
    lookahead      the same, routed through the app and played on to the speakers
                   a few seconds late, so the show sees what is coming
                   (lib/routing.py, lib/lookahead.py)
    track:<name>   a file in music/, looped in real time and played through
                   the speakers unless DIRTY_LEDS_MUTE=1
    pipe:<path>    raw s16le mono PCM at MIC_RATE from a FIFO, e.g. written by
                   librespot, shairport-sync or snapclient
"""
import os
import shutil
import subprocess
import threading
import time
import numpy as np
import config

MUSIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "music")
TRACK_EXTENSIONS = (".mp3", ".flac", ".wav", ".ogg", ".opus", ".m4a", ".aac")


def _rate():
    return config.settings["configuration"]["MIC_RATE"]


def _frames_per_buffer():
    return int(_rate() / config.settings["configuration"]["FPS"])


def list_tracks():
    if not os.path.isdir(MUSIC_DIR):
        return []
    tracks = []
    for root, _, files in os.walk(MUSIC_DIR):
        for name in files:
            if name.lower().endswith(TRACK_EXTENSIONS):
                tracks.append(os.path.relpath(os.path.join(root, name), MUSIC_DIR))
    return sorted(tracks)


def available_sources():
    sources = [{"id": "off", "label": "Off", "kind": "live"}]
    try:
        import pyaudio  # noqa: F401
        sources.append({"id": "mic", "label": "Microphone", "kind": "live"})
    except ImportError:
        pass
    if shutil.which("pw-record"):
        sources.append({"id": "system", "label": "System audio", "kind": "live"})
    from lib import routing
    if routing.available():
        sources.append({"id": "lookahead", "label": "System audio with lookahead", "kind": "live"})
    for pipe in config.settings.get("pipes", []):
        sources.append({"id": "pipe:" + pipe["path"], "label": pipe.get("name", pipe["path"]), "kind": "live"})
    if shutil.which("ffmpeg"):
        for track in list_tracks():
            label = os.path.splitext(track)[0].replace(os.sep, " / ")
            sources.append({"id": "track:" + track, "label": label, "kind": "track"})
    return sources


class AudioInput:
    def __init__(self, callback, source="off", on_change=None):
        self.callback = callback
        self.source = source
        self.error = None
        self.on_change = on_change
        self._switch = threading.Event()
        # The track playing and how many frames of it have been played (it loops)
        self.track = None
        self.track_frame = 0
        # The rolling analysis while the lookahead source runs (lib/lookahead.py)
        self.lookahead = None

    def set_source(self, source, trusted=False):
        """Switch source. Untrusted callers (the web UI) may only pick listed sources"""
        if not trusted and source not in [s["id"] for s in available_sources()]:
            raise ValueError("Unknown audio source: {}".format(source))
        self.source = source
        self.error = None
        self._switch.set()

    def run(self):
        while True:
            self._switch.clear()
            source = self.source
            try:
                self._run_source(source)
            except Exception as error:
                self.error = "{}: {}".format(source, error)
                print("dirty-leds: audio source failed, " + self.error)
                if self.on_change:
                    self.on_change()
                # Keep rendering non-reactive effects until a new source is picked
                self._run_silence()

    def _run_source(self, source):
        if source == "off":
            self._run_silence()
        elif source == "mic":
            self._run_mic()
        elif source == "system":
            self._run_command(self._system_capture_command())
        elif source == "lookahead":
            self._run_lookahead()
        elif source.startswith("track:"):
            self.track = source[len("track:"):]
            self.track_frame = 0
            try:
                self._run_command(self._file_decode_command(os.path.join(MUSIC_DIR, self.track)),
                                  play=os.environ.get("DIRTY_LEDS_MUTE") != "1", paced=True)
            finally:
                self.track = None
        elif source.startswith("pipe:"):
            self._run_pipe(source[len("pipe:"):])

    def _run_silence(self):
        frame = np.zeros(_frames_per_buffer(), dtype=np.float32)
        interval = 1.0 / config.settings["configuration"]["FPS"]
        next_frame = time.time()
        while not self._switch.is_set():
            self.callback(frame)
            next_frame += interval
            delay = next_frame - time.time()
            if delay > 0:
                self._switch.wait(delay)
            else:
                next_frame = time.time()

    def _run_mic(self):
        import pyaudio
        p = pyaudio.PyAudio()
        frames_per_buffer = _frames_per_buffer()
        stream = p.open(format=pyaudio.paInt16,
                        channels=1,
                        rate=_rate(),
                        input=True,
                        frames_per_buffer=frames_per_buffer)
        try:
            while not self._switch.is_set():
                data = stream.read(frames_per_buffer, exception_on_overflow=False)
                self.callback(np.frombuffer(data, dtype=np.int16).astype(np.float32))
        finally:
            stream.stop_stream()
            stream.close()
            p.terminate()

    def _run_lookahead(self):
        """System audio through the app: analysed as it arrives, played to the
        speakers and shown on the lights `lookahead` seconds later"""
        import select
        from collections import deque
        from lib import routing
        from lib.lookahead import RollingAnalysis

        output = routing.VirtualOutput()
        rolling = RollingAnalysis(delay_seconds=config.settings.get("lookahead", 8.0))
        capture = player = None
        try:
            format_args = ["--format", "s16", "--rate", str(_rate()), "--channels", "2", "-"]
            capture = subprocess.Popen(["pw-record", "--target", routing.NODE_NAME,
                                        "-P", "{ stream.capture.sink=true }"] + format_args, stdout=subprocess.PIPE)
            if os.environ.get("DIRTY_LEDS_MUTE") != "1":
                player = subprocess.Popen(["pw-play", "--target", output.speakers] + format_args,
                                          stdin=subprocess.PIPE, bufsize=0)
            self.lookahead = rolling
            samples = _frames_per_buffer()
            chunk_bytes = samples * 4  # stereo, 16 bit
            frame_time = samples / _rate()
            silent_chunk = bytes(chunk_bytes)
            delayed = deque()
            pending = b""
            fd = capture.stdout.fileno()
            start = time.monotonic()
            emitted = 0  # frames processed, to keep time when nothing is playing
            while not self._switch.is_set():
                ready, _, _ = select.select([fd], [], [], frame_time)
                if ready:
                    data = os.read(fd, 65536)
                    if not data:
                        raise RuntimeError("system audio capture stopped")
                    pending += data
                else:
                    # Nothing playing: the virtual output goes quiet. After a quarter of a
                    # second of that, carry on with silence at the real rate (keeps the
                    # lights running and marks gaps between songs). Audio arrives in
                    # bursts longer than a frame, so shorter gaps are normal
                    behind = (time.monotonic() - start) / frame_time - emitted
                    if behind > 0.25 / frame_time:
                        pending += silent_chunk * int(behind)
                while len(pending) >= chunk_bytes:
                    chunk, pending = pending[:chunk_bytes], pending[chunk_bytes:]
                    emitted += 1
                    mono = np.frombuffer(chunk, dtype=np.int16).reshape(-1, 2).mean(axis=1).astype(np.float32)
                    rolling.push(mono)
                    delayed.append((chunk, mono))
                    if len(delayed) > rolling.delay:
                        heard_chunk, heard = delayed.popleft()
                        if player is not None:
                            player.stdin.write(heard_chunk)
                        self.callback(heard)
                    else:
                        # Still filling the delay: keep the lights rendering
                        self.callback(np.zeros(samples, dtype=np.float32))
        finally:
            self.lookahead = None
            rolling.close()
            for process in (capture, player):
                if process is not None:
                    process.kill()
                    process.wait()
            output.close()

    def _run_pipe(self, path):
        chunk_bytes = _frames_per_buffer() * 2
        with open(path, "rb") as pipe:
            while not self._switch.is_set():
                chunk = pipe.read(chunk_bytes)
                if len(chunk) < chunk_bytes:
                    raise RuntimeError("pipe closed")
                self.callback(np.frombuffer(chunk, dtype=np.int16).astype(np.float32))

    def _system_capture_command(self):
        if not shutil.which("pw-record"):
            raise RuntimeError("capturing system audio needs PipeWire (pw-record)")
        # stream.capture.sink records the monitor of the default output instead of a mic
        return ["pw-record", "-P", "{ stream.capture.sink=true }",
                "--format", "s16", "--rate", str(_rate()), "--channels", "1", "-"]

    def _file_decode_command(self, path):
        if not shutil.which("ffmpeg"):
            raise RuntimeError("playing tracks needs ffmpeg")
        # -stream_loop -1 repeats the file forever. Pacing is done by _run_command,
        # ffmpeg's -re releases audio in bursts which makes the LEDs stutter
        return ["ffmpeg", "-loglevel", "error", "-stream_loop", "-1", "-i", path,
                "-f", "s16le", "-ac", "1", "-ar", str(_rate()), "-"]

    def _playback_command(self):
        if shutil.which("pw-play"):
            return ["pw-play", "--format", "s16", "--rate", str(_rate()), "--channels", "1", "-"]
        if shutil.which("aplay"):
            return ["aplay", "-q", "-f", "S16_LE", "-r", str(_rate()), "-c", "1"]
        return None

    def _run_command(self, command, play=False, paced=False):
        """Read raw s16le mono from a subprocess, optionally echoing it to the speakers

        paced: the source produces audio faster than real time (a file), so
        release one frame per frame interval
        """
        source = subprocess.Popen(command, stdout=subprocess.PIPE)
        player = None
        if play:
            player_command = self._playback_command()
            if player_command:
                player = subprocess.Popen(player_command, stdin=subprocess.PIPE, bufsize=0)
            else:
                print("dirty-leds: No pw-play or aplay found, track will play silently")

        chunk_bytes = _frames_per_buffer() * 2
        interval = _frames_per_buffer() / _rate()
        next_frame = time.time()
        try:
            while not self._switch.is_set():
                chunk = source.stdout.read(chunk_bytes)
                if len(chunk) < chunk_bytes:
                    raise RuntimeError("stopped unexpectedly: {}".format(" ".join(command)))
                if paced:
                    next_frame += interval
                    delay = next_frame - time.time()
                    if delay > 0:
                        time.sleep(delay)
                    elif delay < -0.25:
                        # Fell far behind (e.g. a slow effect), don't try to catch up
                        next_frame = time.time()
                if player:
                    player.stdin.write(chunk)
                self.callback(np.frombuffer(chunk, dtype=np.int16).astype(np.float32))
                self.track_frame += 1
        finally:
            source.kill()
            source.wait()
            if player:
                player.kill()
                player.wait()
