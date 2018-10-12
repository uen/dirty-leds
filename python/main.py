from __future__ import print_function
from __future__ import division
from scipy.ndimage.filters import gaussian_filter1d
from collections import deque
import time
import sys
import numpy as np
import config
import lib.microphone as microphone
from lib.dsp import ExpFilter
#import lib.led as led
import lib.devices as devices
import lib.bottle as bottle
import logging
import subprocess
from threading import Thread
import datetime
import lib.api as api
import random
import socket
import util
from visualizer import Visualizer
from lib.dsp import DSP

class Board():
    def __init__(self, board):
        self.board = board
        self.config = config.settings["devices"][board]["configuration"]
        self.effectConfig = config.settings["devices"][board]["effect_opts"]
        self.visualizer = Visualizer(self)
        self.signalProcessor = DSP(self)
    
        self.esp = devices.ESP8266(
            auto_detect   = self.config["AUTO_DETECT"],
            mac_addr      = self.config["MAC_ADDR"],
            ip            = self.config["UDP_IP"],
            port          = self.config["UDP_PORT"]
        )


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


#### HACK for laser ####
import socket
laserSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)



def microphone_update(audio_samples):
    global y_roll, prev_rms, prev_exp, prev_fps_update

    b = next(iter(boards))
    
    # Get processed audio data for each device
    audio_datas = {}
    for board in boards:
        audio_datas[board] = boards[board].signalProcessor.update(audio_samples)
        
    outputs = {}

    for board in boards:
            # Get visualization output for each board
        audio_input = audio_datas[board]["vol"] > config.settings["configuration"]["MIN_VOLUME_THRESHOLD"]
        outputs[board] = boards[board].visualizer.get_vis(audio_datas[board]["mel"], audio_input)

        if(config.settings["sync"]):
            boards[board].esp.show(outputs[b])
        else:
            boards[board].esp.show(outputs[board])


    # FPS update
    fps = frames_per_second()
    if time.time() - 0.5 > prev_fps_update:
        prev_fps_update = time.time()

    if config.settings["configuration"]["displayFPS"]:
        print('FPS {:.0f} / {:.0f}'.format(fps, config.settings["configuration"]["FPS"]))



boards = {}
for board in config.settings["devices"]:
    boards[board] = Board(board)

prev_fps_update = time.time()
# The previous time that the frames_per_second() function was called
_time_prev = time.time() * 1000.0
# The low-pass filter used to estimate frames-per-second
_fps = ExpFilter(val=config.settings["configuration"]["FPS"], alpha_decay=0.2, alpha_rise=0.2)




apiThread = None

api.setBoards(boards)
api.setConfig(config)

if __name__ == "__main__":
    apiThread = Thread(target=bottle.run, kwargs=dict(host=socket.gethostname(), port=8082, debug=True))
    apiThread.daemon = True
    apiThread.start()





microphone.start_stream(microphone_update)
