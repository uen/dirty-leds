import math
import time

import config


class Effect():
    nonReactive = False
    effectName = "Effect"

    def __init__(self, visualizer):
        pass

    def visualize(self, board, y):
        pass

    def steps(self, interval):
        """Animation steps due since the last call, for effects that move every `interval` seconds

        Lets an effect animate slower than the frame rate without holding up
        the audio loop. An interval of 0 or less steps once per frame.
        """
        if interval <= 0:
            return 1
        now = time.monotonic()
        last = getattr(self, "_last_step", None)
        if last is None:
            self._last_step = now
            return 1
        count = int((now - last) / interval)
        self._last_step = last + count * interval
        return count

    @staticmethod
    def dynamics(features, floor=0.3):
        """Brightness scale that follows how big the music is: `floor` in a breakdown, 1 in a drop"""
        return floor + (1.0 - floor) * features.intensity

    @staticmethod
    def fade(seconds):
        """Per-frame multiplier that fades something to about a third over `seconds`"""
        if seconds <= 0:
            return 0.0
        return math.exp(-1.0 / (seconds * config.settings["configuration"]["FPS"]))
