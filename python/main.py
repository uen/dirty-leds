import argparse
import os
import time

parser = argparse.ArgumentParser(description="Music reactive LED strips")
parser.add_argument("--config", help="device config to use instead of config.json, e.g. rooms/living-room.json")
parser.add_argument("--audio", default="off",
                    help="off, mic, system, track:<file in music/> or pipe:<fifo path>")
parser.add_argument("--host", help="web interface host (default from config, 127.0.0.1)")
parser.add_argument("--port", type=int, help="web interface port (default from config, 8000)")
if __name__ == "__main__":
    args = parser.parse_args()
    if args.config:
        os.environ["DIRTY_LEDS_CONFIG"] = args.config

import config
import lib.devices as devices
import lib.api as api
import lib.server as server
from lib.audio import AudioInput
from lib.dsp import ExpFilter, DSP
from lib.features import MusicFeatures
from threading import Thread
from visualizer import Visualizer

class Board():
    def __init__(self, board):
        self.board = board
        self.config = config.settings["devices"][board]["configuration"]
        self.effectConfig = config.settings["devices"][board]["effect_opts"]
        self.visualizer = Visualizer(self)
        self.signalProcessor = DSP(self)
    
        self.esp = devices.ESP8266(
            ip            = self.config["UDP_IP"],
            port          = self.config["UDP_PORT"],
            leds          = self.config["N_PIXELS"]
        )
    @property
    def features(self):
        """This frame's music features (lib.features.Features), shared by every board"""
        return music.current

    def getProfile(self):
        return {
            "currentEffect": self.config["current_effect"],
            "effectConfig": self.effectConfig
        }
       
    def setProfile(self, profile):
        self.config["current_effect"] = profile["currentEffect"]
        # Merge so effects added since the profile was saved keep their defaults
        for effect, options in profile["effectConfig"].items():
            self.effectConfig.setdefault(effect, {}).update(options)


def frames_per_second():
    """ Return the estimated frames per second

    Returns the current estimate for frames-per-second (FPS).
    FPS is estimated by measured the amount of time that has elapsed since
    this function was previously called. The FPS estimate is low-pass filtered
    to reduce noise.

    This function is intended to be called one time for every iteration of
    the program's main loop.

    Returns
    -------
    fps : float
        Estimated frames-per-second. This value is low-pass filtered
        to reduce noise.
    """
    global _time_prev, _fps
    time_now = time.time() * 1000.0
    dt = time_now - _time_prev
    _time_prev = time_now
    if dt == 0.0:
        return _fps.value
    return _fps.update(1000.0 / dt)


def analyse(audio_samples):
    """Audio analysis per board. Boards with the same frequency range share one analysis.
    Also updates the music features every board reads through Board.features"""
    music.update(audio_samples)
    results = {}
    for board in boards.values():
        analyser = board.signalProcessor.analyser
        if analyser not in results:
            results[analyser] = analyser.update(audio_samples)
    return {name: results[board.signalProcessor.analyser] for name, board in boards.items()}


def lead_board():
    """The board whose frame every board shows when sync is on: the longest strip"""
    return max(boards.values(), key=lambda board: board.config["N_PIXELS"])


def render(board, audio_data):
    """One board's frame: its effect's output scaled by the master brightness"""
    audio_input = not board.features.silent
    # New array: effects may return their own state, which must not be dimmed in place
    return board.visualizer.get_vis(audio_data["mel"], audio_input) * config.settings["brightness"]


def render_all(audio_datas):
    """Frames for every board. With sync on, the lead board's frame is shared by all"""
    if config.settings["sync"]:
        lead = lead_board()
        output = render(lead, audio_datas[lead.board])
        return {name: output for name in boards}
    return {name: render(board, audio_datas[name]) for name, board in boards.items()}


def send_all(outputs):
    for name, board in boards.items():
        board.esp.show(outputs[name])


def microphone_update(audio_samples):
    global prev_fps_update

    audio_datas = analyse(audio_samples)
    server.broadcaster.set_features(music.current)
    send_all(render_all(audio_datas))

    # FPS update
    fps = frames_per_second()
    if time.time() - 0.5 > prev_fps_update:
        prev_fps_update = time.time()
        if config.settings["configuration"]["displayFPS"]:
            print('FPS {:.0f} / {:.0f}'.format(fps, config.settings["configuration"]["FPS"]))


music = MusicFeatures()
boards = {}
for board in config.settings["devices"]:
    boards[board] = Board(board)


prev_fps_update = time.time()
# The previous time that the frames_per_second() function was called
_time_prev = time.time() * 1000.0
# The low-pass filter used to estimate frames-per-second
_fps = ExpFilter(val=config.settings["configuration"]["FPS"], alpha_decay=0.2, alpha_rise=0.2)

def run(audio_source="off", host=None, port=None):
    """Start the web interface and the audio loop in a background thread"""
    api.setBoards(boards)
    api.setConfig(config)

    audio = AudioInput(microphone_update, on_change=api.notify)
    audio.set_source(audio_source, trusted=True)
    api.setAudio(audio)

    host = host or config.settings["server"]["host"]
    port = port or config.settings["server"]["port"]
    server.start(boards, host, port)
    print("dirty-leds: web interface at http://{}:{}".format(host, port))

    audioThread = Thread(target=audio.run, daemon=True)
    audioThread.start()
    return audioThread


if __name__ == "__main__":
    from tools.make_test_tracks import generate
    generate()
    try:
        run(args.audio, args.host, args.port).join()
    except KeyboardInterrupt:
        pass
