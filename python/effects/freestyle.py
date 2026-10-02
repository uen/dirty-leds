"""Freestyle: a look built from layers whose knobs glide with the music

Layers, combined the way overlapping light mixes (screen blend), so they never
clip to white:

    base    the palette laid along the strip as a slow colour field that
            drifts and breathes with the bass
    flow    colour injected at the origin travels outward and fades (like
            Scroll); groove accents push bright pulses into it
    hits    shapes fired by the music: a flash of the whole strip, a ripple
            that travels out, a block at the hit's step in the bar (a repeating
            rhythm draws itself along the strip), or a chase that steps across
            the room one beat at a time
    impact  the drop: a white flash on every strip and a shockwave of colour
            crossing the room, fired when the "impact" option changes

Everything is computed along a 0-1 "position" from the origin outward. The
shape decides where each LED sits on it: linear (from one end), mirror (from
the centre) or room (along the room, from the strips' 3D layout, so things
travel across strips). Positions, colours and every level and speed glide
toward their targets, so the look morphs instead of cutting.

Standalone it picks a mood from the song's energy itself. In the auto show the
director (lib/director.py, following a plan from lib/choreography.py for
pre-analysed tracks) sets the knob targets every frame, bumps "snap" to jump
straight to them and "impact" to fire the drop.
"""
import math

import numpy as np

import config
import util
from lib.geometry import room_positions

from effects.effect import Effect

RESOLUTION = 200  # cells along the position axis
MAX_HITS = 24
TIERS = ("calm", "groove", "peak")

# Continuous knobs: default value and glide time in beats
KNOBS = {
    "master": (1.0, 0.5),  # overall level of the layers (not the impact)
    "base_level": (0.1, 1.0),
    "base_drift": (0.3, 2.0),  # palette lengths per minute
    "base_breathe": (0.5, 2.0),
    "flow_level": (0.6, 1.0),
    "flow_beats": (2.0, 2.0),  # beats for the flow to cross the strip
    "flow_trail": (1.0, 2.0),  # seconds
    "hit_level": (0.6, 1.0),
    "hit_size": (0.15, 1.0),  # share of the strip a hit covers
    "hit_decay": (0.3, 1.0),  # seconds
    "saturation": (1.0, 1.0),  # 1 full colour, 0 washed out to white
}
# Discrete knobs, switched rather than glided
CHOICES = {
    "hit_style": "ripple",  # flash, ripple, block or chase
    "hit_source": "groove",  # groove, kick, snare, beat, eighth or sixteenth
    "shape": "mirror",  # linear, mirror or room
    "direction": 1,  # 1 outward, -1 inward
}

# Moods per energy tier, used standalone and by the director as a starting point.
# Dark gaps matter as much as light: peaks keep the base low so hits have contrast
MOODS = {
    "calm": {"master": 0.8, "base_level": 0.22, "base_drift": 0.6, "base_breathe": 0.7, "flow_level": 0.2,
             "flow_beats": 8.0, "flow_trail": 2.0, "hit_level": 0.25, "hit_size": 0.3, "hit_decay": 0.8,
             "saturation": 0.9, "hit_style": "ripple", "hit_source": "beat"},
    "groove": {"master": 0.9, "base_level": 0.06, "base_drift": 0.3, "base_breathe": 0.5, "flow_level": 0.65,
               "flow_beats": 2.0, "flow_trail": 0.8, "hit_level": 0.6, "hit_size": 0.1, "hit_decay": 0.25,
               "saturation": 1.0, "hit_style": "block", "hit_source": "groove"},
    "peak": {"master": 1.0, "base_level": 0.02, "base_drift": 0.2, "base_breathe": 0.4, "flow_level": 0.8,
             "flow_beats": 1.0, "flow_trail": 0.45, "hit_level": 1.0, "hit_size": 0.18, "hit_decay": 0.22,
             "saturation": 1.0, "hit_style": "ripple", "hit_source": "groove"},
    # The bars before a drop: fast flow, quick hits, colour draining toward white
    "build": {"master": 0.9, "base_level": 0.02, "base_drift": 1.0, "base_breathe": 0.2, "flow_level": 0.9,
              "flow_beats": 0.5, "flow_trail": 0.35, "hit_level": 0.7, "hit_size": 0.07, "hit_decay": 0.1,
              "saturation": 0.5, "hit_style": "block", "hit_source": "eighth"},
}
TIER_START = {"groove": 0.35, "peak": 0.72}
WHITE = np.array([255.0, 255.0, 255.0])


def _blend(a, b):
    """Screen blend of two 0-255 light layers: adds up like light without clipping"""
    return a + b - a * b / 255.0


class Freestyle(Effect):
    def __init__(self, visualizer):
        self.effectName = "Freestyle"
        self.board = visualizer.board
        self.n = self.board.config["N_PIXELS"]
        self.knobs = {name: default for name, (default, _) in KNOBS.items()}
        self.choices = dict(CHOICES)
        self.flow = np.zeros((3, RESOLUTION))
        self.flow_offset = 0.0
        self.drift = 0.0
        self.breath = 0.0
        self.hits = []  # [age in seconds, origin position, colour, strength, style]
        self.palette = None
        self.lut = None  # palette colours along the position axis, gliding to the target palette
        self.target_lut = None
        self.positions = None  # where each LED sits on the position axis, gliding between shapes
        self.room = room_positions(self.board.board, self.n)
        self.snap_seen = None
        self.impact_seen = None
        self.impact_age = None
        self.impact_colour = WHITE
        self.tier = "calm"
        self.last_phase = 0.0
        self.last_step = -1
        self.beats = 0

    # Targets ---------------------------------------------------------------

    def _targets(self, board, features):
        options = board.effectConfig["Freestyle"]
        if options.get("auto", True):
            mood = self._mood(features)
            targets = dict(MOODS[mood])
            targets["shape"] = options.get("shape", "mirror")
            level = options.get("level", 1.0)
            for name in ("base_level", "flow_level", "hit_level"):
                targets[name] *= level
            snapped = features.section_change and mood == "peak"
            if snapped:
                self._fire_impact()
            return targets, options.get("color_mode", "Dancefloor"), snapped
        snap = options.get("snap")
        snapped = snap is not None and snap != self.snap_seen
        self.snap_seen = snap
        impact = options.get("impact")
        if impact is not None and impact != self.impact_seen:
            if self.impact_seen is not None:
                self._fire_impact()
            self.impact_seen = impact
        return options, options.get("color_mode", "Dancefloor"), snapped

    def _mood(self, features):
        """Standalone: the song's energy tier, and a build in the bars before a known drop"""
        beat = 60.0 / max(features.tempo, 60)
        if features.until_drop is not None and features.until_drop <= 8 * beat:
            return "build"
        if features.prepared and features.tier:
            self.tier = features.tier
            return self.tier
        # Live: tiers from intensity, easier to stay in than to enter
        current = TIERS.index(self.tier)
        level = 0
        for i, name in enumerate(TIERS[1:], start=1):
            threshold = TIER_START[name] + (-0.07 if current >= i else 0.07)
            if features.intensity >= threshold:
                level = i
        self.tier = TIERS[level]
        return self.tier

    def _glide(self, targets, features, snap):
        beat = 60.0 / max(features.tempo, 60)
        fps = config.settings["configuration"]["FPS"]
        for name, (_, glide_beats) in KNOBS.items():
            if name not in targets:
                continue
            target = float(targets[name])
            if snap:
                self.knobs[name] = target
            else:
                rate = 1.0 - math.exp(-1.0 / (glide_beats * beat * fps))
                self.knobs[name] += (target - self.knobs[name]) * rate
        for name in CHOICES:
            if name in targets:
                self.choices[name] = targets[name]

    # Geometry and colour ---------------------------------------------------

    def _target_positions(self):
        n = self.n
        shape = self.choices["shape"]
        index = np.arange(n) / max(n - 1, 1)
        if shape == "room" and self.room is not None:
            positions = self.room
        elif shape == "linear":
            positions = index
        else:
            positions = np.abs(2 * index - 1)
        if self.choices["direction"] < 0:
            positions = 1.0 - positions
        return positions

    def _update_geometry(self, board, palette, snap):
        target = self._target_positions()
        rate = 1.0 if snap or self.positions is None else 0.08
        self.positions = target if self.positions is None else self.positions + (target - self.positions) * rate

        if palette != self.palette or self.lut is None:
            self.palette = palette
            gradient = board.visualizer.gradient(palette)[:, :self.n].astype(float)
            self.target_lut = util.interpolate_rows(gradient, RESOLUTION)
            if self.lut is None or snap:
                self.lut = self.target_lut.copy()
        self.lut += (self.target_lut - self.lut) * (1.0 if snap else 0.05)

    def _colour(self, position):
        """Palette colour at a 0-1 position (wrapping)"""
        return self.lut[:, int((position % 1.0) * (RESOLUTION - 1))]

    # Layers ----------------------------------------------------------------

    def _base(self, features, dt):
        self.drift = (self.drift + self.knobs["base_drift"] / 60.0 * dt) % 1.0
        self.breath += (features.bass - self.breath) * (1.0 - math.exp(-dt / 0.4))
        cells = (np.arange(RESOLUTION) / RESOLUTION * 0.5 + self.drift) % 1.0
        colours = self.lut[:, (cells * (RESOLUTION - 1)).astype(int)]
        level = self.knobs["base_level"] * (1.0 - self.knobs["base_breathe"] * (1.0 - self.breath))
        return colours * level

    def _flow(self, features, dt):
        # Tempo-locked: crosses the whole position axis in flow_beats beats, on any strip length
        cells_per_second = RESOLUTION * features.tempo / 60.0 / max(self.knobs["flow_beats"], 0.1)
        self.flow_offset += cells_per_second * dt
        shift = min(int(self.flow_offset), RESOLUTION)
        self.flow_offset -= int(self.flow_offset)
        if shift:
            self.flow[:, shift:] = self.flow[:, :RESOLUTION - shift]
            self.flow[:, :shift] = 0
        self.flow *= math.exp(-dt / max(self.knobs["flow_trail"], 0.05))
        # Bass, mids and treble take the start, middle and end of the palette. Cubed so
        # the flow is broken up into pulses with dark gaps rather than a steady stream
        colours = np.stack([self._colour(0.0), self._colour(0.5), self._colour(0.95)], axis=1)
        bands = np.array([features.bass, features.mid, features.treble]) ** 3
        injected = colours @ bands
        if features.groove_hit or (features.kick_hit and not features.groove_strength):
            injected = injected + self._colour(max(features.bar_step, 0) / 16.0)
        self.flow[:, :max(shift, 1)] = np.minimum(injected, 255)[:, np.newaxis]
        return self.flow * self.knobs["flow_level"]

    def _fired(self, features):
        source = self.choices["hit_source"]
        crossed_half = self.last_phase < 0.5 <= features.beat_phase
        crossed_quarter = int(self.last_phase * 4) != int(features.beat_phase * 4)
        self.last_phase = features.beat_phase
        step_changed = features.bar_step != self.last_step
        self.last_step = features.bar_step
        if source == "eighth":
            return features.beat or crossed_half
        if source == "sixteenth":
            return step_changed if features.bar_step >= 0 else (features.beat or crossed_quarter)
        if source == "groove":
            return features.groove_hit if features.groove_strength else features.kick_hit
        return {"kick": features.kick_hit, "snare": features.snare_hit, "beat": features.beat}.get(source, False)

    def _hits(self, features, dt):
        self.beats += features.beat
        if self._fired(features):
            style = self.choices["hit_style"]
            step = max(features.bar_step, 0)
            if style == "block":
                origin = step / 16.0
            elif style == "chase":
                # Step across the room: one of 8 spots per beat, so it travels strip to strip
                origin = (self.beats % 8) / 8.0 + 1 / 16
            else:
                origin = 0.0
            self.hits.append([0.0, origin, self._colour(step / 16.0 + 0.25), 1.0, style])
            self.hits = self.hits[-MAX_HITS:]
        field = np.zeros((3, RESOLUTION))
        cells = np.arange(RESOLUTION) / RESOLUTION
        size = max(self.knobs["hit_size"], 0.02)
        decay = max(self.knobs["hit_decay"], 0.05)
        crossing = max(self.knobs["flow_beats"], 0.25) * 60.0 / max(features.tempo, 60)
        alive = []
        for hit in self.hits:
            age, origin, colour, strength, style = hit
            if style == "flash":
                shape = np.full(RESOLUTION, math.exp(-age / decay))
            elif style in ("block", "chase"):
                width = size / 2 if style == "block" else max(size, 0.1) / 2
                shape = np.exp(-((cells - origin) / width) ** 4) * math.exp(-age / decay)
            else:  # ripple: a soft front travelling out with a tail behind it
                front = age / crossing
                behind = cells <= front
                shape = np.where(behind, np.exp(-(front - cells) / (size * 2)),
                                 np.exp(-((cells - front) / (size / 2)) ** 2))
                shape = shape * max(0.0, 1.0 - front)
            field += colour[:, np.newaxis] * shape * strength
            hit[0] += dt
            if hit[0] < 6 * decay and (style != "ripple" or hit[0] < crossing):
                alive.append(hit)
        self.hits = alive
        return np.minimum(field, 255) * self.knobs["hit_level"]

    def _fire_impact(self):
        self.impact_age = 0.0
        # The shockwave takes the brightest colour of the new palette
        if self.target_lut is not None:
            brightest = int(np.argmax(self.target_lut.sum(axis=0)))
            self.impact_colour = self.target_lut[:, brightest]
        self.hits = []

    def _impact(self, features, dt):
        """The drop: a white flash fading over half a beat, and a shockwave of colour
        crossing the room in a beat. Sampled at room positions so it sweeps the room"""
        if self.impact_age is None:
            return None
        beat = 60.0 / max(features.tempo, 60)
        age = self.impact_age
        self.impact_age += dt
        if age > 2 * beat:
            self.impact_age = None
            return None
        positions = self.room if self.room is not None else np.abs(2 * np.arange(self.n) / max(self.n - 1, 1) - 1)
        flash = 255.0 * math.exp(-age / (0.6 * beat))
        front = age / beat
        wave = np.where(positions <= front, np.exp(-(front - positions) / 0.2),
                        np.exp(-((positions - front) / 0.06) ** 2)) * max(0.0, 1.0 - front / 2)
        return np.minimum(flash + self.impact_colour[:, np.newaxis] * wave * 1.2, 255)

    # Render ----------------------------------------------------------------

    def visualize(self, board, y):
        features = board.features
        dt = 1.0 / config.settings["configuration"]["FPS"]
        targets, palette, snap = self._targets(board, features)
        self._glide(targets, features, snap)
        self._update_geometry(board, palette, snap)

        field = _blend(_blend(self._base(features, dt), self._flow(features, dt)), self._hits(features, dt))
        # Each LED samples the field at its position
        index = np.clip((self.positions * (RESOLUTION - 1)).astype(int), 0, RESOLUTION - 1)
        output = field[:, index] * self.dynamics(features, floor=0.6) * self.knobs["master"]
        saturation = self.knobs["saturation"]
        if saturation < 0.999:
            # Drain colour toward white at the same brightness
            peak = output.max(axis=0, keepdims=True)
            output = peak + (output - peak) * saturation
        impact = self._impact(features, dt)
        if impact is not None:
            output = _blend(np.minimum(output, 255), impact)
        return util.blur(np.minimum(output, 255), 1.0)
