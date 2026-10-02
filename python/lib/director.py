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

# Effects that suit each energy tier. The longest strip leads with one and
# every other strip gets a different one, so the room is varied. Only effects
# that move in a structured way (flowing, rolling, pulsing on the beat); Sparkle
# and Power scatter random pixels, so the show leaves them out
POOLS = {
    "calm": ["Wavelength", "Spectrum", "Scroll"],
    "groove": ["Scroll", "Spectrum", "Bars", "Reactive Runner", "Wavelength", "Ripple", "Energy"],
    "peak": ["Pulse", "Ripple", "Energy", "Scroll", "Spectrum", "Bars"],
}
# The last bars before a known drop: every strip together, tightening toward the hit
BUILD_EFFECTS = ["Scroll", "Pulse"]
BUILD_BEATS = 8
# Unison is a moment, not the norm: the first bars after a drop, then the strips split up
UNISON_AFTER_DROP_BEATS = 16
# Chance that a groove or peak phrase puts every strip on one effect anyway
UNISON_CHANCE = 0.15
# Chance each supporting strip is switched off in a calm part, so drops light the room up
CALM_OFF_CHANCE = 0.35

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
        # The lead effect, each strip's effect, and when a unison look splits up
        self.look = {"lead": None, "strips": {}, "split_after": None}
        self.palette = PALETTES["calm"][0]
        self.beats_in_look = 0
        self.pending = None  # why the look should change on the next beat
        self.transition = 0.5
        self.generation = 0
        self.assignments = {}
        # Brightness for every strip on the show; dips to black just before a drop
        self.level = 1.0
        self.building = False
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
        if features.prepared:
            self._follow_map(features)
            return
        self.level = 1.0
        self.building = False
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

        if self._split_unison(features):
            return
        phrase_beats = 4 * self._phrase_bars()
        if self.pending is None and self.beats_in_look >= phrase_beats:
            self.pending = "phrase"
        if self.pending and features.beat and (self.beats_in_look >= MIN_BEATS_PER_LOOK or self.pending == "drop"):
            self._new_look(self.pending, features)

    def _follow_map(self, features):
        """With a pre-analysed track: switch exactly at section starts, build into
        drops that are coming, and black out for the last half beat before them"""
        beat = 60.0 / max(features.tempo, 60)
        if features.section_change or (features.tier != self.tier and not self.building):
            rising = TIERS.index(features.tier) > TIERS.index(self.tier)
            self.tier = features.tier
            self.building = False
            self.level = 1.0
            self._new_look("drop" if self.tier == "peak" and rising else "section", features)
            return
        build_time = BUILD_BEATS * beat
        if features.until_drop is not None and features.until_drop <= build_time:
            if not self.building:
                self.building = True
                self._new_look("build", features)
            self._ramp_build(1.0 - features.until_drop / build_time)
            self.level = 0.05 if features.until_drop <= beat / 2 else 1.0
            return
        self.level = 1.0
        self.beats_in_look += features.beat
        if self._split_unison(features):
            return
        if features.beat and self.beats_in_look >= 4 * self._phrase_bars():
            self._new_look("phrase", features)

    def _split_unison(self, features):
        """End a unison look after its bars: the lead keeps going, the others diverge"""
        split_after = self.look["split_after"]
        if split_after is not None and features.beat and self.beats_in_look >= split_after:
            self._new_look("split", features)
            return True
        return False

    def _ramp_build(self, progress):
        """Speed up and tighten the build look as the drop gets closer"""
        for assignment in self.assignments.values():
            if assignment.effect == "Scroll":
                assignment.options["speed"] = 2 + round(8 * progress)
                assignment.options["trail"] = 1.2 - 0.8 * progress
            elif assignment.effect == "Pulse":
                assignment.options["sharpness"] = 1.0 + 3.0 * progress

    def assignment(self, board):
        """The board's effect and options for this frame"""
        self.requested = True
        if not self.assignments:
            self._new_look("start", self.music.current)
        return self.assignments.get(board.board) or self._assign(board, self.music.current)

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
        ranked = [board.board for board in sorted(self.boards.values(), key=lambda b: -b.config["N_PIXELS"])]
        previous_lead = self.look["lead"]
        split_after = None
        if reason == "build":
            lead = self._pick(BUILD_EFFECTS, features, previous_lead)
            strips = dict.fromkeys(ranked, lead)
        elif reason == "split":
            # Same lead effect for continuity, everyone else goes their own way
            lead = previous_lead
            strips = self._cast(lead, ranked, features)
        else:
            lead = self._pick(POOLS[self.tier], features, previous_lead)
            unison = reason == "drop" or (self.tier != "calm" and self.rng.random() < UNISON_CHANCE)
            if unison:
                strips = dict.fromkeys(ranked, lead)
                split_after = UNISON_AFTER_DROP_BEATS
            else:
                strips = self._cast(lead, ranked, features)
        self.look = {"lead": lead, "strips": strips, "split_after": split_after}

        if reason in ("start", "drop", "energy", "section") or (reason == "phrase" and self.rng.random() < 0.5):
            palettes = [p for p in PALETTES[self.tier] if p != self.palette] or PALETTES[self.tier]
            self.palette = self.rng.choice(palettes)
        # Cut straight in on a drop for impact, otherwise crossfade over a beat
        self.transition = 0.0 if reason == "drop" else 60.0 / max(features.tempo, 60)
        self.beats_in_look = 0
        self.pending = None
        self.generation += 1
        self.assignments = {name: self._assign(board, features) for name, board in self.boards.items()}
        if self.on_change:
            self.on_change()

    def _pick(self, pool, features, avoid):
        """Choose an effect, favouring Scroll when the song has a strong repeating
        rhythm (it plays the pattern back best) but not twice in a row"""
        def weight(effect):
            if effect == avoid:
                return 0.1
            if effect == "Scroll":
                return 1.0 + 2.0 * features.groove_strength
            return 1.0
        return self.rng.choices(pool, weights=[weight(e) for e in pool])[0]

    def _cast(self, lead, ranked, features):
        """The lead effect on the longest strip, a different effect on each of the others"""
        others = [e for e in POOLS[self.tier] if e != lead]
        self.rng.shuffle(others)
        strips = {}
        for i, name in enumerate(ranked):
            if i == 0:
                strips[name] = lead
            elif self.tier == "calm" and self.rng.random() < CALM_OFF_CHANCE:
                strips[name] = "Off"
            else:
                strips[name] = others[(i - 1) % len(others)] if others else lead
        return strips

    def _assign(self, board, features):
        effect = self.look["strips"].get(board.board) or self.look["lead"]
        assignment = Assignment(effect, transition=self.transition)
        options = copy.deepcopy(board.effectConfig.get(assignment.config_key, {}))
        if "color_mode" in options:
            options["color_mode"] = self.palette
        options.update(self._tuned(effect, features))
        assignment.options = options
        return assignment

    def _tuned(self, effect, features):
        """Options that suit the current tempo and energy"""
        fast = features.tempo >= 125
        peak = self.tier == "peak"
        if effect == "Scroll":
            return {"speed": {"calm": 2, "groove": 3, "peak": 5}[self.tier] + (1 if fast else 0),
                    "trail": {"calm": 1.5, "groove": 1.0, "peak": 0.6}[self.tier],
                    "mirror": True, "blur": 0.8}
        if effect == "Ripple":
            return {"beats": 2.0 if fast else 1.5, "width": 10.0 if peak else 7.0, "on_beat": peak}
        if effect == "Pulse":
            return {"sharpness": 3.0 if peak else 2.0, "colours": 4}
        if effect == "Sparkle":
            return {"fade": 0.2 if peak else 0.35}
        if effect == "Wavelength":
            return {"roll_speed": 0 if peak else 1, "mirror": True}
        if effect == "Spectrum":
            return {"blur": 2.0 if self.tier == "calm" else 1.0}
        if effect == "Bars":
            return {"roll_speed": 1, "mirror": True}
        return {}
