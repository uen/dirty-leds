import math

import numpy as np
import config

from effects.effect import Effect
from lib.geometry import room_positions

WHITE = np.array([255.0, 255.0, 255.0])


class Auto(Effect):
    """The auto show: renders whatever the director picked for this strip,
    crossfading when the look changes, and draws the drop's impact over it"""
    def __init__(self, visualizer):
        self.effectName = "Auto"
        self.visualizer = visualizer
        self.current = None  # (assignment, effect instance)
        self.previous = None
        self.blend_frames = 0
        self.blend_left = 0
        n = visualizer.board.config["N_PIXELS"]
        room = room_positions(visualizer.board.board, n)
        # Where the shockwave passes each LED: across the room, or out from the middle
        self.positions = room if room is not None else np.abs(2 * np.arange(n) / max(n - 1, 1) - 1)
        self.impact_seen = None
        self.impact_age = None
        self.impact_colour = WHITE

    def visualize(self, board, y):
        show = board.show
        assignment = show.assignment(board)
        if self.current is None or assignment is not self.current[0]:
            # A fresh instance per assignment: the outgoing and incoming looks never
            # share state (so an effect isn't stepped twice a frame while they blend),
            # and an effect doesn't come back with a buffer left from minutes ago
            effect = type(self.visualizer.effects[assignment.effect])(self.visualizer)
            self.previous, self.current = self.current, (assignment, effect)
            self.blend_frames = int(assignment.transition * config.settings["configuration"]["FPS"])
            self.blend_left = self.blend_frames if self.previous else 0

        output = self._render(board, *self.current, y)
        if self.blend_left > 0:
            mix = 1 - self.blend_left / self.blend_frames
            output = self._render(board, *self.previous, y) * (1 - mix) + output * mix
            self.blend_left -= 1
        else:
            self.previous = None
        output = output * show.strip_brightness(board.board)

        if show.impact != self.impact_seen:
            if self.impact_seen is not None:
                self._fire_impact(board, assignment)
            self.impact_seen = show.impact
        impact = self._impact(board.features)
        if impact is not None:
            # Screen blend: adds up like light without clipping
            output = np.minimum(output, 255)
            output = output + impact - output * impact / 255.0
        return output

    def _fire_impact(self, board, assignment):
        self.impact_age = 0.0
        # The shockwave takes the brightest colour of the new look's palette
        palette = assignment.options.get("color_mode")
        if palette:
            gradient = board.visualizer.gradient(palette).astype(float)
            self.impact_colour = gradient[:, int(np.argmax(gradient.sum(axis=0)))]
        else:
            self.impact_colour = WHITE

    def _impact(self, features):
        """The drop: a white flash on every strip fading over half a beat, and a
        shockwave of colour crossing the room in a beat"""
        if self.impact_age is None:
            return None
        beat = 60.0 / max(features.tempo, 60)
        age = self.impact_age
        self.impact_age += 1.0 / config.settings["configuration"]["FPS"]
        if age > 2 * beat:
            self.impact_age = None
            return None
        flash = 255.0 * math.exp(-age / (0.6 * beat))
        front = age / beat
        positions = self.positions
        wave = np.where(positions <= front, np.exp(-(front - positions) / 0.2),
                        np.exp(-((positions - front) / 0.06) ** 2)) * max(0.0, 1.0 - front / 2)
        return np.minimum(flash + self.impact_colour[:, np.newaxis] * wave * 1.2, 255)

    @staticmethod
    def _render(board, assignment, effect, y):
        """Render an effect with the director's options in place of the strip's own"""
        own = board.effectConfig
        board.effectConfig = {**own, assignment.config_key: assignment.options}
        try:
            return np.asarray(effect.visualize(board, y), dtype=float)
        finally:
            board.effectConfig = own
