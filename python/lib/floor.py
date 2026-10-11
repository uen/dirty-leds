"""Minimum brightness for a strip while music is playing.

Effects that flash or chase can drop LEDs to black between hits, which reads as
flicker. With a floor set, any LED below it keeps the last colour it showed,
held at the floor level, so the strip dims instead of switching off. With no
music the floor is off and the strip can go fully dark.
"""
import numpy as np


class BrightnessFloor:
    def __init__(self):
        # Last colour each LED showed, scaled so its brightest channel is 1
        self.hue = None

    def apply(self, frame, level, active):
        """frame: (3, n) values 0-255. level: floor as 0-1 of full brightness"""
        if level <= 0 or not active:
            return frame
        n = frame.shape[1]
        if self.hue is None or self.hue.shape[1] != n:
            self.hue = np.zeros((3, n))

        floor = level * 255
        peak = frame.max(axis=0)
        lit = peak >= floor
        # Any LED with a visible colour remembers it, even a dim one
        coloured = peak > 2
        self.hue[:, coloured] = frame[:, coloured] / peak[coloured]

        # LEDs that have never been lit borrow the frame's average colour, else warm white
        unseen = self.hue.max(axis=0) == 0
        if unseen.any():
            fill = self.hue[:, coloured].mean(axis=1) if coloured.any() else np.array([1.0, 0.8, 0.6])
            self.hue[:, unseen] = (fill / max(fill.max(), 1e-6))[:, None]

        dark = ~lit
        if not dark.any():
            return frame
        output = frame.astype(float, copy=True)
        output[:, dark] = np.maximum(output[:, dark], self.hue[:, dark] * floor)
        return output
