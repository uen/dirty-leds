import time


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
