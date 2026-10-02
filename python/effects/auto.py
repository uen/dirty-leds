import numpy as np
import config

from effects.effect import Effect


class Auto(Effect):
    """The auto show: renders whatever the director picked for this strip,
    crossfading when the look changes"""
    def __init__(self, visualizer):
        self.effectName = "Auto"
        self.visualizer = visualizer
        self.current = None  # (assignment, effect instance)
        self.previous = None
        self.blend_frames = 0
        self.blend_left = 0

    def visualize(self, board, y):
        assignment = board.show.assignment(board)
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
        return output * board.show.level

    @staticmethod
    def _render(board, assignment, effect, y):
        """Render an effect with the director's options in place of the strip's own"""
        own = board.effectConfig
        board.effectConfig = {**own, assignment.config_key: assignment.options}
        try:
            return np.asarray(effect.visualize(board, y), dtype=float)
        finally:
            board.effectConfig = own
