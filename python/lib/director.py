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

import numpy as np

from effects.freestyle import MOODS as FREESTYLE_MOODS
from lib import choreography
from lib.geometry import room_positions

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
# Each tier has its own visual language: calm is soft and slow, grooves move,
# peaks are bold and hit on the beat
POOLS = {
    "calm": ["Wavelength", "Spectrum"],
    "groove": ["Scroll", "Spectrum", "Bars", "Reactive Runner", "Wavelength", "Ripple", "Energy"],
    "peak": ["Pulse", "Ripple", "Energy", "Scroll", "Bars"],
}
# Overall brightness of the show per tier, on top of each effect's own dynamics,
# so drops are clearly the brightest moments and calm parts sit back
TIER_LEVEL = {"calm": 0.65, "groove": 0.8, "peak": 1.0}
# A drop opens with an effect that fills the strips, not a sparse one
DROP_EFFECTS = ["Pulse", "Scroll", "Energy"]
# The last bars before a known drop: every strip together, tightening toward the hit
BUILD_EFFECTS = ["Scroll", "Pulse", "Freestyle"]
# How Freestyle is favoured as the lead in "mixed" style, per tier
FREESTYLE_LEAD_WEIGHT = {"calm": 1.5, "groove": 4.0, "peak": 4.0}
# Freestyle variations the show rotates through every few bars
FREESTYLE_SHAPES = ["mirror", "room", "linear"]
FREESTYLE_HITS = {"calm": ["ripple"], "groove": ["block", "ripple"], "peak": ["ripple", "block", "flash"]}
BUILD_BEATS = 8
# Unison is a moment, not the norm: the first bars after a drop, then the strips split up
UNISON_AFTER_DROP_BEATS = 16
# Chance that a groove or peak phrase puts every strip on one effect anyway
UNISON_CHANCE = 0.15
# Chance each supporting strip is switched off in a calm part, so drops light the room up
CALM_OFF_CHANCE = 0.35

# Peaks only get palettes with several distinct hues; near single-colour ones
# turned a whole drop into one wash
PALETTES = {
    "calm": ["Ocean", "Sunset", "Peach", "Romantic"],
    "groove": ["Sunny", "Fruity", "Jungle", "Ocean", "Dancefloor", "Peach"],
    "peak": ["Dancefloor", "Spectral", "Sunny", "Fruity", "Jungle"],
}
# A smaller change every this many bars within a look, so long sections don't go stale
VARY_BARS = 4
# How much an effect's recent use counts against picking it again, decaying each look
USAGE_DECAY = 0.6
# A strip that isn't the one lit in a solo scene keeps this much of its light
SOLO_FLOOR = 0.0
# How fast a strip lights up and goes dark when the solo light moves on, per frame
SOLO_ATTACK = 0.6
SOLO_RELEASE = 0.18
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
        self.support_palette = PALETTES["calm"][1]
        self.mirror = True
        self.usage = {}
        # Freestyle knobs the show is steering toward
        self.freestyle_shape = "mirror"
        self.freestyle_hits = "ripple"
        self.snap = 0
        self.impact = 0
        # The planned show for a pre-analysed track (lib/choreography.py)
        self.plan_for = None
        self.cues = []
        self.cue = None
        self.variation = 0
        self.second_impact_at = None
        # Live show (no pre-analysis): drops so far, scenes so far
        self.live_drops = 0
        self.live_scenes = 0
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
        # Solo scenes: how lit each strip is (0-1), and the order the light travels in
        self.gates = {}
        self._room_order = None

    @property
    def brightness(self):
        """What the auto show multiplies every strip by: the tier's level, and the
        blackout before a drop"""
        level = self.cue.level if self.cue is not None else 1.0
        return self.level * TIER_LEVEL[self.tier] * level

    def strip_brightness(self, name):
        """brightness, and for a solo scene whether this strip has the light"""
        return self.brightness * self.gates.get(name, 1.0)

    def room_order(self):
        """Strip names in the order they sit across the room, for the solo light to
        travel along. Strips without a layout keep the longest-first order"""
        if self._room_order is None:
            def place(item):
                i, board = item
                positions = room_positions(board.board, board.config["N_PIXELS"])
                return (0, float(np.mean(positions))) if positions is not None else (1, i)
            boards = sorted(self.boards.values(), key=lambda b: -b.config["N_PIXELS"])
            self._room_order = [b.board for _, b in sorted(enumerate(boards), key=place)]
        return self._room_order

    def _update_gates(self, features):
        """Solo: every strip dark but one, the light passing to the next strip on each
        beat (or bar), there and back across the room. Otherwise every strip is lit"""
        names = self.room_order()
        lit = None
        if self.cue is not None and self.cue.mode == "solo" and len(names) > 1:
            steps = self.beats_in_look // (4 if self.cue.solo_step == "bar" else 1)
            cycle = 2 * len(names) - 2
            step = steps % cycle
            lit = names[step if step < len(names) else cycle - step]
        for name in names:
            target = 1.0 if lit is None or name == lit else SOLO_FLOOR
            gate = self.gates.get(name, 1.0)
            rate = SOLO_ATTACK if target > gate else SOLO_RELEASE
            self.gates[name] = gate + (target - gate) * rate

    def active(self):
        return self.requested or any(board.config["current_effect"] == "Auto" for board in self.boards.values())

    def update(self):
        """Once per frame, after the music features"""
        if not self.active():
            return
        self.requested = False
        features = self.music.current
        style = self._style()
        if features.prepared and features.analysis is not None and style != "effects":
            self._follow_plan(features)
        elif style != "effects":
            self._follow_live_show(features)
        else:
            self.cue = None
            if features.prepared:
                self._follow_map(features)
            else:
                self._follow_live(features)
        self._update_gates(features)
        self._steer_freestyle(features)

    def _follow_live_show(self, features):
        """No pre-analysis (mic, system audio): the same scenes as a planned show,
        started by what is heard. Drops land on the bass slamming in or the energy
        rising into a peak; scenes change with the energy and every few bars"""
        self.level = 1.0
        tier = self._tier(features.intensity)
        rising_to_peak = tier == "peak" and TIERS.index(tier) > TIERS.index(self.tier)
        settled = False
        if tier == self.tier:
            self.candidate = None
        else:
            if tier != self.candidate:
                self.candidate, self.candidate_beats = tier, 0
            self.candidate_beats += features.beat
            settled = self.candidate_beats >= BEATS_TO_SETTLE
        self.beats_in_look += features.beat

        if features.drop_hit or rising_to_peak:
            self.tier = "peak"
            self.candidate = None
            self.live_drops += 1
            self._live_cue("drop", features)
            return
        if settled:
            self.tier = tier
            self.candidate = None
            self._live_cue("scene", features)
            return
        if self.cue is None:
            self._live_cue("scene", features)
            return
        if self.cue.kind == "drop" and self.beats_in_look >= 4 * choreography.DROP_BARS:
            self._live_cue("scene", features)
            return
        building = features.build > 0.55 and self.tier != "peak"
        if building and self.cue.kind != "build":
            self._live_cue("build", features)
            return
        if self.cue.kind == "build" and features.build < 0.35:
            self._live_cue("scene", features)
            return
        if features.beat and self.beats_in_look >= 4 * choreography.SCENE_BARS:
            self._live_cue("scene", features)
            return
        self._cue_variation(features)

    def _live_cue(self, kind, features):
        palettes = choreography.PALETTES["peak" if kind == "drop" else self.tier]
        palette = self.rng.choice([p for p in palettes if p != self.palette] or palettes)
        support = self.rng.choice([p for p in palettes if p != palette] or palettes)
        if kind == "drop":
            # Escalate over the first few drops of a song
            cue = choreography._drop_cue(0, 0, palette, support, self.live_drops - 1, False,
                                         min(1.0, (self.live_drops - 1) / 3), self.rng, self._style(),
                                         self.look.get("lead"))
            self.impact += 1
            self.snap += 1
        elif kind == "build":
            cue = choreography._build_cue(0, 0, palette, self.rng, self._style())
        else:
            self.live_scenes += 1
            shape = choreography.SHAPES[self.live_scenes % len(choreography.SHAPES)]
            cue = choreography._scene_cue(0, 0, self.tier, palette, support, shape, self.live_scenes, self._style(),
                                          self.rng, max(0, self.live_drops - 1) if self.tier == "peak" else 0, False,
                                          self.look.get("lead"))
        self.cue = cue
        self.variation = 0
        self._cast_cue(cue, features)

    def _cue_variation(self, features):
        """Variations every few bars inside a scene: shapes rotate, the others change direction"""
        cue = self.cue
        if cue.kind in ("peak", "groove", "calm") and features.beat and self.beats_in_look \
                and self.beats_in_look % (4 * VARY_BARS) == 0:
            self.variation += 1
            if cue.sparse or cue.lead_effect != "Freestyle":
                # Freestyle varies its own shapes; anything else (and sparse scenes, without
                # a beat to play with) has its colours change places, crossfading over a beat
                self.palette, self.support_palette = self.support_palette, self.palette
                self.transition = 60.0 / max(features.tempo, 60)
                self.assignments = {name: self._assign(board, features) for name, board in self.boards.items()}
            if self.on_change:
                self.on_change()

    def _follow_plan(self, features):
        """With a pre-analysed track: play the show planned for it, cue by cue"""
        analysis = features.analysis
        frame = int(round(features.position * analysis.fps)) % analysis.frames
        if self.plan_for is not analysis:
            # A newer analysis (lookahead re-analyses the song as it arrives): re-plan
            self.cues = choreography.plan(analysis, self._style(), seed=self.plan_seed(analysis))
            self.plan_for = analysis
        cue = next((c for c in self.cues if c.start <= frame < c.end), self.cues[-1] if self.cues else None)
        if cue is None:
            return
        # A scene that has started runs to its own end even if a re-plan moved things
        # around; only a drop or build the new plan has found here interrupts it
        if self.cue is not None and cue is not self.cue and self.cue.start <= frame < self.cue.end \
                and not (cue.kind in ("drop", "build") and cue.kind != self.cue.kind):
            cue = self.cue
        beat = 60.0 / max(features.tempo, 60)
        if cue is not self.cue and self.cue is not None and cue.kind == self.cue.kind and cue.tier == self.cue.tier \
                and abs(cue.start - self.cue.start) <= 2 * analysis.fps:
            # The same scene, continued by a newer plan that has heard further into the
            # song: carry on with it rather than starting the look (or the drop) again
            self.cue = cue
        if cue is not self.cue:
            self.cue = cue
            self.tier = cue.tier
            self.variation = 0
            if cue.kind == "drop":
                self.impact += 1
                self.snap += 1
                # The last drop hits twice: again one bar in
                self.second_impact_at = frame + int(4 * beat * analysis.fps) if cue.final else None
            self._cast_cue(cue, features)
        if self.second_impact_at is not None and frame >= self.second_impact_at:
            self.impact += 1
            self.second_impact_at = None
        self.building = cue.kind == "build"
        self.beats_in_look += features.beat
        if self.building and cue.end > cue.start:
            self._ramp_build(min(1.0, max(0.0, (frame - cue.start) / (cue.end - cue.start))))
        self._cue_variation(features)
        # Fade to black over the last two beats before the drop and hold the dark for
        # the last half beat, so the drop lands out of nothing
        if self.building and features.until_drop is not None and features.until_drop <= 2 * beat:
            self.level = max(0.0, (features.until_drop - beat / 2) / (beat * 1.5)) ** 2
        else:
            self.level = 1.0

    def plan_seed(self, analysis):
        """The same song keeps the same plan when it is re-planned from a longer analysis"""
        if not hasattr(self, "_plan_seed") or analysis.frames < getattr(self, "_seed_frames", 0):
            self._plan_seed = self.rng.random()
        self._seed_frames = analysis.frames
        return self._plan_seed

    def _cast_cue(self, cue, features):
        """Unison and solo put every strip on the cue's effect; split gives the longest
        strip the effect and each of the others one of the cue's supporting effects"""
        ranked = self._ranked()
        strips = {}
        for i, name in enumerate(ranked):
            if i == 0 or cue.mode != "split" or not cue.support_effects:
                strips[name] = cue.lead_effect
            else:
                strips[name] = cue.support_effects[(i - 1) % len(cue.support_effects)]
        self.look = {"lead": cue.lead_effect, "strips": strips, "split_after": None,
                     "signature": "{} {} {} {} {}".format(cue.kind, cue.mode, cue.shape, cue.palette,
                                                          "/".join(sorted(set(strips.values()))))}
        self.palette, self.support_palette = cue.palette, cue.support_palette
        self.freestyle_shape = cue.shape
        # Straight in on a drop, otherwise crossfade over a beat
        self.transition = 0.0 if cue.kind == "drop" else 60.0 / max(features.tempo, 60)
        self.beats_in_look = 0
        self.generation += 1
        self.assignments = {name: self._assign(board, features) for name, board in self.boards.items()}
        if self.on_change:
            self.on_change()

    def _follow_live(self, features):
        """Without a pre-analysed track: react to the live features"""
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
        elif self.pending is None and features.beat and self.beats_in_look \
                and self.beats_in_look % (4 * VARY_BARS) == 0 and self.look["split_after"] is None:
            self._vary(features)
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
        self._phrase(features)

    def _phrase(self, features):
        """A new look every phrase, a variation every VARY_BARS within it"""
        if not features.beat or not self.beats_in_look:
            return
        if self.beats_in_look >= 4 * self._phrase_bars():
            self._new_look("phrase", features)
        elif self.beats_in_look % (4 * VARY_BARS) == 0 and self.look["split_after"] is None:
            self._vary(features)

    def _vary(self, features):
        """Supporting strips swap effects with each other, or change palette and
        direction; the lead keeps going so it doesn't restart"""
        strips = self.look["strips"]
        supports = [name for name in self._ranked()[1:] if strips.get(name) not in (None, "Off")]
        effects = [strips[name] for name in supports]
        if len(set(effects)) > 1:
            for name, effect in zip(supports, effects[1:] + effects[:1]):
                strips[name] = effect
        else:
            others = [p for p in PALETTES[self.tier] if p not in (self.palette, self.support_palette)]
            self.support_palette = self.rng.choice(others or PALETTES[self.tier])
        self.mirror = not self.mirror
        # Freestyle morphs instead: a new shape and hit style, glided into
        self.freestyle_shape = FREESTYLE_SHAPES[(FREESTYLE_SHAPES.index(self.freestyle_shape) + 1) % len(FREESTYLE_SHAPES)]
        self.freestyle_hits = self.rng.choice(FREESTYLE_HITS[self.tier])
        self.transition = 60.0 / max(features.tempo, 60)
        for name in supports:
            self.assignments[name] = self._assign(self.boards[name], features)
        if self.on_change:
            self.on_change()

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

    def _style(self):
        for board in self.boards.values():
            if board.config["current_effect"] == "Auto":
                return board.effectConfig["Auto"].get("style", "mixed")
        return "mixed"

    def _steer_freestyle(self, features):
        """Set the knob targets of every strip showing Freestyle, each frame"""
        if not self.assignments:
            return
        lead = self._ranked()[0]
        for name, assignment in self.assignments.items():
            if assignment.effect == "Freestyle":
                assignment.options.update(self._freestyle_targets(name == lead, features))

    def _freestyle_targets(self, leads, features):
        if self.cue is not None:
            return self._planned_targets(leads, features)
        mood = "build" if self.building else self.tier
        targets = dict(FREESTYLE_MOODS[mood])
        targets.update({"auto": False, "snap": self.snap, "shape": self.freestyle_shape})
        if mood != "build":
            # Straight after a drop everything flashes; after that the rotating hit style
            targets["hit_style"] = "flash" if self.look["split_after"] is not None and mood == "peak" else self.freestyle_hits
        if not leads:
            # Supporting strips answer the lead: flow the other way, hit on snares
            targets["direction"] = -1
            if targets["hit_source"] == "groove":
                targets["hit_source"] = "snare"
            if mood == "calm":
                targets["flow_level"] *= 0.4
                targets["hit_level"] = 0.0
        else:
            targets["direction"] = 1
        return targets

    def _planned_targets(self, leads, features):
        """Knob targets from the current cue of the plan"""
        cue = self.cue
        mood = {"drop": "peak", "build": "build"}.get(cue.kind, cue.tier)
        targets = dict(FREESTYLE_MOODS[mood])
        shapes = choreography.SHAPES
        # The lead and the others never share a shape, and both rotate every few bars
        shape_index = shapes.index(cue.shape) + self.variation + (0 if leads else 1)
        shape = "room" if cue.kind == "drop" else shapes[shape_index % len(shapes)]
        targets.update({"auto": False, "snap": self.snap, "shape": shape,
                        "direction": 1 if leads or self.variation % 2 == 0 else -1})
        targets.update(cue.lead if leads else cue.support)
        if cue.kind == "build":
            analysis = features.analysis
            if analysis is not None and cue.end > cue.start:
                frame = int(round(features.position * analysis.fps))
                progress = min(1.0, max(0.0, (frame - cue.start) / max(cue.end - cue.start, 1)))
            else:
                # Live there is no knowing when the drop comes: follow how hard it is building
                progress = min(1.0, features.build)
            targets.update(choreography.build_targets(cue, progress, 60.0 / max(features.tempo, 60),
                                                      features.until_drop))
        return targets

    def _ranked(self):
        """Strip names, longest first"""
        return [board.board for board in sorted(self.boards.values(), key=lambda b: -b.config["N_PIXELS"])]

    def _new_look(self, reason, features):
        ranked = self._ranked()
        previous_lead = self.look["lead"]
        split_after = None
        style = self._style()
        if reason == "drop":
            self.snap += 1
            self.impact += 1
            self.freestyle_hits = self.rng.choice(FREESTYLE_HITS["peak"])
        if style == "freestyle" and reason != "split":
            self.freestyle_shape = self.rng.choice(FREESTYLE_SHAPES)
            strips = dict.fromkeys(ranked, "Freestyle")
            lead = "Freestyle"
            split_after = UNISON_AFTER_DROP_BEATS if reason == "drop" else None
        elif reason == "build":
            lead = self._pick(BUILD_EFFECTS if style == "mixed" else BUILD_EFFECTS[:2], features, previous_lead)
            strips = dict.fromkeys(ranked, lead)
        elif reason == "split":
            # Same lead effect for continuity, everyone else goes their own way
            lead = previous_lead
            strips = self._cast(lead, ranked, features) if style != "freestyle" else dict.fromkeys(ranked, lead)
        else:
            pool = DROP_EFFECTS if reason == "drop" else POOLS[self.tier]
            if style == "mixed":
                pool = pool + ["Freestyle"]
            lead = self._pick(pool, features, previous_lead)
            unison = reason == "drop" or (self.tier != "calm" and self.rng.random() < UNISON_CHANCE)
            if unison:
                strips = dict.fromkeys(ranked, lead)
                split_after = UNISON_AFTER_DROP_BEATS
            else:
                strips = self._cast(lead, ranked, features)
        self.look = {"lead": lead, "strips": strips, "split_after": split_after}
        for effect in self.usage:
            self.usage[effect] *= USAGE_DECAY
        for effect in strips.values():
            self.usage[effect] = self.usage.get(effect, 0.0) + 1.0 / len(strips)
        self.mirror = self.rng.random() < 0.6

        if reason in ("start", "drop", "energy", "section") or (reason == "phrase" and self.rng.random() < 0.5):
            palettes = [p for p in PALETTES[self.tier] if p != self.palette] or PALETTES[self.tier]
            self.palette = self.rng.choice(palettes)
        if reason != "build":
            others = [p for p in PALETTES[self.tier] if p != self.palette] or PALETTES[self.tier]
            self.support_palette = self.rng.choice(others)
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
            if effect == "Freestyle":
                base = FREESTYLE_LEAD_WEIGHT[self.tier]
            elif effect == "Scroll":
                base = 1.0 + 2.0 * features.groove_strength
            else:
                base = 1.0
            # Effects used a lot lately are less likely, so no one effect takes over
            return base / (1.0 + 2.0 * self.usage.get(effect, 0.0))
        return self.rng.choices(pool, weights=[weight(e) for e in pool])[0]

    def _cast(self, lead, ranked, features):
        """The lead effect on the longest strip, a different effect on each of the others.
        A Freestyle lead may have a Freestyle answering it on the next strip"""
        others = [e for e in POOLS[self.tier] if e != lead]
        self.rng.shuffle(others)
        if lead == "Freestyle" and self.tier != "calm" and self.rng.random() < 0.5:
            others.insert(0, "Freestyle")
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
            first = board.board == self._ranked()[0]
            # In a planned show the longest strip leads and, unless the scene is split,
            # everyone shares its palette; otherwise strips sharing the lead effect do
            if self.cue is not None:
                leads = first or self.cue.mode != "split"
            else:
                leads = first or effect == self.look["lead"]
            options["color_mode"] = self.palette if leads else self.support_palette
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
                    "mirror": self.mirror, "blur": 0.8}
        if effect == "Ripple":
            return {"beats": 2.0 if fast else 1.5, "width": 10.0 if peak else 7.0, "on_beat": peak}
        if effect == "Pulse":
            # Softer on a drop so the strips stay full between hits
            drop = self.cue is not None and self.cue.kind == "drop"
            return {"sharpness": 1.5 if drop else 2.0, "colours": 4}
        if effect == "Sparkle":
            return {"fade": 0.2 if peak else 0.35}
        if effect == "Wavelength":
            return {"roll_speed": 0 if peak else 1, "mirror": self.mirror}
        if effect == "Spectrum":
            return {"blur": 2.0 if self.tier == "calm" else 1.0}
        if effect == "Bars":
            return {"roll_speed": 1, "mirror": self.mirror}
        if effect == "Wipe":
            return {"speed": 0.5 if peak else 0.75, "colours": 4,
                    "direction": self.rng.choice(["centre", "left", "right"])}
        if effect == "Bounce":
            return {"size": 0.1 if peak else 0.07, "trail": 0.2 if peak else 0.12}
        if effect == "Stack":
            return {"mirror": self.mirror or self.building}
        if effect == "Bloom":
            return {"size": 0.9 if peak else 0.7}
        return {}
