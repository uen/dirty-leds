"""Calm: per-strip smoothing over time, so a strip follows the song's bigger moves
instead of twitching on every small change.

Each LED eases toward the effect's value. Rising is quicker than falling, so a real
hit still lands but lingers, while flickers shorter than the easing time average out.
0 is off (raw effect), 1 is the calmest.
"""
import time

import numpy as np

# Easing times in seconds at calm = 1; they scale linearly down to 0
MAX_RISE = 0.35
MAX_FALL = 1.2


class Calm:
    def __init__(self):
        self.value = None
        self.last = None

    def apply(self, frame, level):
        now = time.monotonic()
        dt = 0.0 if self.last is None else min(now - self.last, 0.25)
        self.last = now
        if level <= 0 or self.value is None or self.value.shape != frame.shape:
            self.value = frame.astype(float, copy=True)
            return frame

        rise = np.exp(-dt / (MAX_RISE * level))
        fall = np.exp(-dt / (MAX_FALL * level))
        keep = np.where(frame > self.value, rise, fall)
        self.value = self.value * keep + frame * (1 - keep)
        return self.value.copy()
