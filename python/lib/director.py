"""Auto show: picks the effect, options and colours for every strip on Auto

The director follows the song's energy (calm, groove or peak, from the music
features' intensity) and chooses a look for it: a main effect for the longest
strip and a supporting effect for the others, all sharing one palette. Looks
change on the beat when a drop hits, when the song moves to a new section, or
after a number of bars so the show never sits still. Each effect's options
are tuned to the tempo and energy instead of left at their defaults.
"""
import copy
import random
from dataclasses import dataclass, field

TIERS = ("calm", "groove", "peak")
# Intensity where each tier starts; leaving needs a margin so it doesn't flicker on the edge
TIER_START = {"groove": 0.35, "peak": 0.72}
HYSTERESIS = 0.07
MIN_BEATS_PER_LOOK = 8
# A new energy tier has to hold this many beats before the look follows it,
# except a jump up to peak, which cuts in straight away
BEATS_TO_SETTLE = 2

# A look is (main effect, its options), (supporting effect, its options)
LOOKS = {
    "calm": [
        (("Wavelength", {"roll_speed": 1}), ("Sparkle", {"density": 0.03, "fade": 0.4})),
        (("Sparkle", {"density": 0.04, "fade": 0.5}), ("Wavelength", {})),
        (("Spectrum", {"blur": 1.5}), ("Sparkle", {"density": 0.02})),
    ],
    "groove": [
        (("Scroll", {}), ("Wavelength", {})),
        (("Spectrum", {}), ("Scroll", {})),
        (("Bars", {"resolution": 6}), ("Sparkle", {})),
        (("Reactive Runner", {}), ("Energy", {})),
        (("Wavelength", {}), ("Ripple", {})),
    ],
    "peak": [
        (("Pulse", {}), ("Ripple", {})),
        (("Ripple", {"on_beat": True}), ("Pulse", {})),
        (("Energy", {}), ("Ripple", {})),
        (("Power", {}), ("Pulse", {})),
        (("Scroll", {}), ("Ripple", {})),
    ],
}
PALETTES = {
    "calm": ["Ocean", "Sunset", "Peach", "Romantic"],
    "groove": ["Sunny", "Fruity", "Jungle", "Ocean", "Dancefloor", "Peach"],
    "peak": ["Dancefloor", "Spectral", "Sexy", "Rust", "Fruity"],
}
# Effects whose options live under a different key in effect_opts
CONFIG_KEYS = {"Reactive Runner": "RunnerReactive"}


@dataclass
class Assignment:
    """What one strip shows: an effect with the options to render it with"""
    effect: str
    options: dict = field(default_factory=dict)
    # Seconds to crossfade from the previous assignment, 0 for a hard cut
    transition: float = 0.5

    @property
    def config_key(self):
        return CONFIG_KEYS.get(self.effect, self.effect)


class Director:
    def __init__(self, boards, music, on_change=None):
        self.boards = boards
        self.music = music
        self.on_change = on_change
        self.tier = "calm"
        self.candidate = None
        self.candidate_beats = 0
        self.look = LOOKS["calm"][0]
        self.palette = PALETTES["calm"][0]
        self.beats_in_look = 0
        self.pending = None  # why the look should change on the next beat
        self.transition = 0.5
        self.generation = 0
        self.assignments = {}
        # Set when any strip asked for an assignment since the last update
        self.requested = False
        self.rng = random.Random()

    def active(self):
        return self.requested or any(board.config["current_effect"] == "Auto" for board in self.boards.values())

    def update(self):
        """Once per frame, after the music features"""
        if not self.active():
            return
        self.requested = False
        features = self.music.current
        tier = self._tier(features.intensity)
        if tier == self.tier:
            self.candidate = None
        else:
            if tier != self.candidate:
                self.candidate, self.candidate_beats = tier, 0
            self.candidate_beats += features.beat
            rising_to_peak = tier == "peak" and TIERS.index(tier) > TIERS.index(self.tier)
            if rising_to_peak or self.candidate_beats >= BEATS_TO_SETTLE:
                self.tier = tier
                self.candidate = None
                self.pending = "drop" if rising_to_peak else "energy"
        if features.section_change:
            self.pending = self.pending or "section"
        self.beats_in_look += features.beat

        phrase_beats = 4 * self._phrase_bars()
        if self.pending is None and self.beats_in_look >= phrase_beats:
            self.pending = "phrase"
        if self.pending and features.beat and (self.beats_in_look >= MIN_BEATS_PER_LOOK or self.pending == "drop"):
            self._new_look(self.pending, features)

    def assignment(self, board):
        """The board's effect and options for this frame"""
        self.requested = True
        if not self.assignments:
            self._new_look("start", self.music.current)
        return self.assignments.get(board.board) or self._assign(board, self._role(board), self.music.current)

    def _tier(self, intensity):
        current = TIERS.index(self.tier)
        level = 0
        for i, name in enumerate(TIERS[1:], start=1):
            start = TIER_START[name]
            # Easier to stay in a tier than to enter it
            threshold = start - HYSTERESIS if current >= i else start + HYSTERESIS
            if intensity >= threshold:
                level = i
        return TIERS[level]

    def _phrase_bars(self):
        for board in self.boards.values():
            if board.config["current_effect"] == "Auto":
                return board.effectConfig["Auto"]["bars"]
        return 16

    def _new_look(self, reason, features):
        options = [look for look in LOOKS[self.tier] if look != self.look] or LOOKS[self.tier]
        self.look = self.rng.choice(options)
        if reason in ("start", "drop", "energy", "section") or self.rng.random() < 0.5:
            palettes = [p for p in PALETTES[self.tier] if p != self.palette] or PALETTES[self.tier]
            self.palette = self.rng.choice(palettes)
        # Cut straight in on a drop for impact, otherwise crossfade over a beat
        self.transition = 0.0 if reason == "drop" else 60.0 / max(features.tempo, 60)
        self.beats_in_look = 0
        self.pending = None
        self.generation += 1
        self.assignments = {name: self._assign(board, self._role(board), features) for name, board in self.boards.items()}
        if self.on_change:
            self.on_change()

    def _role(self, board):
        """Longest strip leads; the rest alternate between supporting and echoing the lead"""
        ranked = sorted(self.boards.values(), key=lambda b: -b.config["N_PIXELS"])
        names = [b.board for b in ranked]
        index = names.index(board.board) if board.board in names else 0
        return "main" if index % 2 == 0 else "support"

    def _assign(self, board, role, features):
        effect, look_options = self.look[0] if role == "main" else self.look[1]
        assignment = Assignment(effect, transition=self.transition)
        options = copy.deepcopy(board.effectConfig.get(assignment.config_key, {}))
        if "color_mode" in options:
            options["color_mode"] = self.palette
        options.update(self._tuned(effect, features))
        options.update(look_options)
        assignment.options = options
        return assignment

    def _tuned(self, effect, features):
        """Options that suit the current tempo and energy"""
        fast = features.tempo >= 125
        peak = self.tier == "peak"
        if effect == "Scroll":
            return {"speed": 2 if fast or peak else 1, "trail": {"calm": 1.5, "groove": 1.0, "peak": 0.6}[self.tier],
                    "mirror": True, "blur": 0.8}
        if effect == "Ripple":
            return {"beats": 2.0 if fast else 1.5, "width": 10.0 if peak else 7.0}
        if effect == "Pulse":
            return {"sharpness": 3.0 if peak else 2.0, "colours": 4}
        if effect == "Sparkle":
            return {"fade": 0.2 if peak else 0.35}
        if effect == "Wavelength":
            return {"roll_speed": 0 if peak else 1, "mirror": True}
        if effect == "Bars":
            return {"roll_speed": 1, "mirror": True}
        return {}
