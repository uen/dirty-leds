"""Audio input sources

start_stream() feeds the callback one frame of mono int16 samples (as float32)
at a time, MIC_RATE / FPS samples per frame. The source is picked by the
`source` argument or the DIRTY_LEDS_AUDIO environment variable:

    mic          default input device (pyaudio)
    system       whatever is playing on this machine (PipeWire sink monitor)
    <file path>  any file ffmpeg can decode, looped and paced in real time.
                 Also played through the speakers unless DIRTY_LEDS_MUTE=1
"""
import os
import shutil
import subprocess
import time
import numpy as np
import config


def _rate():
    return config.settings["configuration"]["MIC_RATE"]


def _frames_per_buffer():
    return int(_rate() / config.settings["configuration"]["FPS"])


def start_stream(callback, source=None):
    source = source or os.environ.get("DIRTY_LEDS_AUDIO", "mic")
    if source == "mic":
        _stream_mic(callback)
    elif source == "system":
        _stream_command(callback, _system_capture_command())
    else:
        if not os.path.isfile(source):
            raise FileNotFoundError("Audio source is not mic, system or a file: {}".format(source))
        _stream_command(callback, _file_decode_command(source), play=os.environ.get("DIRTY_LEDS_MUTE") != "1")


def _stream_mic(callback):
    import pyaudio
    p = pyaudio.PyAudio()
    frames_per_buffer = _frames_per_buffer()
    stream = p.open(format=pyaudio.paInt16,
                    channels=1,
                    rate=_rate(),
                    input=True,
                    frames_per_buffer=frames_per_buffer)
    overflows = 0
    prev_ovf_time = time.time()
    while True:
        try:
            y = np.frombuffer(stream.read(frames_per_buffer, exception_on_overflow=False), dtype=np.int16)
            y = y.astype(np.float32)
            callback(y)
        except IOError:
            overflows += 1
            if time.time() > prev_ovf_time + 1:
                prev_ovf_time = time.time()
                print('Audio buffer has overflowed {} times'.format(overflows))


def _system_capture_command():
    if not shutil.which("pw-record"):
        raise RuntimeError("Capturing system audio needs PipeWire (pw-record)")
    # stream.capture.sink records the monitor of the default output instead of a mic
    return ["pw-record", "-P", "{ stream.capture.sink=true }",
            "--format", "s16", "--rate", str(_rate()), "--channels", "1", "-"]


def _file_decode_command(path):
    if not shutil.which("ffmpeg"):
        raise RuntimeError("Playing audio files needs ffmpeg")
    # -re paces output at real time, -stream_loop -1 repeats the file forever
    return ["ffmpeg", "-loglevel", "error", "-re", "-stream_loop", "-1", "-i", path,
            "-f", "s16le", "-ac", "1", "-ar", str(_rate()), "-"]


def _playback_command():
    if shutil.which("pw-play"):
        return ["pw-play", "--format", "s16", "--rate", str(_rate()), "--channels", "1", "-"]
    if shutil.which("aplay"):
        return ["aplay", "-q", "-f", "S16_LE", "-r", str(_rate()), "-c", "1"]
    return None


def _stream_command(callback, command, play=False):
    """Read raw s16le mono from a subprocess, optionally echoing it to the speakers"""
    source = subprocess.Popen(command, stdout=subprocess.PIPE)
    player = None
    if play:
        player_command = _playback_command()
        if player_command:
            player = subprocess.Popen(player_command, stdin=subprocess.PIPE, bufsize=0)
        else:
            print("dirty-leds: No pw-play or aplay found, audio file will play silently")

    chunk_bytes = _frames_per_buffer() * 2
    try:
        while True:
            chunk = source.stdout.read(chunk_bytes)
            if len(chunk) < chunk_bytes:
                raise RuntimeError("Audio source ended: {}".format(" ".join(command)))
            if player:
                player.stdin.write(chunk)
            callback(np.frombuffer(chunk, dtype=np.int16).astype(np.float32))
    finally:
        source.kill()
        if player:
            player.kill()
