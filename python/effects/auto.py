from effects.effect import Effect


class Auto(Effect):
    """Cycles through the music effects, changing when the song changes section or every few bars"""
    def __init__(self, visualizer):
        self.effectName = "Auto"
        self.effectKeys = list(visualizer.effects.keys())
        self.autoEffect = 0
        self.beats = 0

    def visualize(self, board, y):
        features = board.features
        self.beats += features.beat
        if features.section_change or self.beats >= 4 * board.effectConfig["Auto"]["bars"]:
            self.autoEffect += 1
            self.beats = 0
        for _ in range(len(self.effectKeys)):
            name = self.effectKeys[self.autoEffect % len(self.effectKeys)]
            effect = board.visualizer.effects[name]
            if name != "Auto" and not effect.nonReactive:
                return effect.visualize(board, y)
            self.autoEffect += 1
        return board.visualizer.prev_output
