"""Plans the auto show for a pre-analysed track before it plays

A lighting designer doesn't react to a song, they plan it: where the builds
start, what the drops do, how the second drop tops the first. With the whole
track analysed (lib/analysis.py) the show can do the same. plan() turns the
track's sections, drops, beats and grooves into cues, each a stretch of beats
with an effect and a way of using the strips:

    unison  every strip on the same effect and palette, like sync (most scenes)
    split   the longest strip leads, each of the others gets its own effect
    solo    every strip dark but one, the light passing along the room on
            each beat (each bar in calm parts)

    drop    the first 4 bars after a drop: an impact (white flash and a
            shockwave across the room, drawn by effects/auto.py) on the
            drop's frame, then every strip together on a beat-locked effect
    peak    the rest of a peak, in 8-bar scenes, mostly unison
    groove  8-bar scenes on the effects that play a groove back (Scroll,
            Bounce, Stack, Wipe...), sometimes split or solo
    calm    slow and soft; sparse, beatless parts drift instead of hitting
    build   the bars leading into a drop, every strip together, tightening
            toward it, then darkness before the impact

Drops escalate: each one is brighter than the one before, and the last one
gets the most colourful palette and an effect that fills every strip.
Freestyle is one effect among the others here, picked now and then.
"""
import random
from dataclasses import dataclass, field

BAR = 4  # beats
SCENE_BARS = 8
# Below this activity a section has no real beat to hit on (ambient, drones, pads)
SPARSE = 0.4
DROP_BARS = 4
MAX_BUILD_BARS = 8
MIN_BUILD_BARS = 2

PALETTES = {
    "calm": ["Ocean", "Sunset", "Peach", "Romantic"],
    "groove": ["Sunny", "Fruity", "Jungle", "Ocean", "Dancefloor", "Peach"],
    # Peaks are mostly unison, so every strip shares one palette: only ones with several hues
    "peak": ["Dancefloor", "Spectral", "Fruity", "Jungle"],
}
FINAL_DROP_PALETTE = "Spectral"
SHAPES = ["mirror", "room", "linear"]
# Effects for each part of a song, with how likely a scene is to pick each.
# Beat-locked effects carry the show; Freestyle only now and then
EFFECTS = {
    "drop": {"Wipe": 3, "Bloom": 3, "Wave": 2, "Pulse": 1},
    "peak": {"Wipe": 3, "Bloom": 3, "Pulse": 2, "Ripple": 2, "Wave": 2, "Scroll": 2, "Bounce": 2, "Freestyle": 0.5},
    "groove": {"Scroll": 3, "Bounce": 2, "Stack": 2, "Wipe": 2, "Bars": 1, "Wavelength": 1, "Spectrum": 1,
               "Reactive Runner": 1, "Freestyle": 0.5},
    "calm": {"Wavelength": 2, "Spectrum": 2, "Freestyle": 2},
    # Solo lights one strip at a time, so it needs an effect that fills that strip
    "solo": {"Scroll": 3, "Wipe": 2, "Bloom": 2, "Wavelength": 1},
    "build": {"Stack": 3, "Scroll": 2, "Pulse": 2},
}
# How a scene uses the strips: all on the same effect (unison, like sync), the
# longest leading with the others each on their own (split), or all dark but one,
# passing the light along the room (solo)
MODES = {
    # Solo leaves a peak too dark: peaks stay full
    "peak": {"unison": 0.75, "split": 0.25},
    "groove": {"unison": 0.55, "split": 0.25, "solo": 0.2},
    "calm": {"unison": 0.5, "split": 0.25, "solo": 0.25},
}


@dataclass
class Cue:
    start: int  # frame
    end: int
    kind: str  # drop, peak, groove, calm or build
    tier: str
    palette: str
    support_palette: str
    shape: str
    lead: dict = field(default_factory=dict)  # Freestyle knob overrides for the lead strip
    support: dict = field(default_factory=dict)  # Freestyle knob overrides for the others
    support_effects: list = field(default_factory=list)  # fixed effects for the others, if any
    escalation: int = 0  # which drop this belongs to, 0 for the first
    final: bool = False
    sparse: bool = False  # no real beat: slow evolving colour instead of hits
    lead_effect: str = "Freestyle"
    mode: str = "unison"  # unison, split or solo
    solo_step: str = "beat"  # solo passes the light on every beat or every bar
    level: float = 1.0  # brightness of the whole scene (drops step up toward the last one)


def _bar_frames(beats, start_frame, end_frame):
    """Frames where bars start between two frames, counted from the first beat at or after start"""
    inside = beats[(beats >= start_frame) & (beats < end_frame)]
    return list(inside[::BAR])


def plan(analysis, style="mixed", seed=None):
    rng = random.Random(seed)
    beats = analysis.beat_frames
    sections = analysis.sections
    drops = set(analysis.drops)
    drop_order = {frame: i for i, frame in enumerate(sorted(drops))}
    cues = []
    previous_palette = None
    last_effect = None

    def contrasting(tier, avoid):
        options = [p for p in PALETTES[tier] if p != avoid] or PALETTES[tier]
        return rng.choice(options)

    shape_index = 0

    def next_shape():
        nonlocal shape_index
        shape_index += 1
        return SHAPES[shape_index % len(SHAPES)]

    for i, section in enumerate(sections):
        next_is_drop = i + 1 < len(sections) and sections[i + 1].start in drops
        is_drop = section.start in drops
        escalation = drop_order.get(section.start, 0)
        # A partial analysis (lookahead) can't know which drop is the last
        partial = getattr(analysis, "partial", False)
        final = is_drop and escalation == len(drops) - 1 and len(drops) > 1 and not partial

        palette = FINAL_DROP_PALETTE if final else contrasting(section.tier, previous_palette)
        support_palette = contrasting(section.tier, palette)
        previous_palette = palette
        bars = _bar_frames(beats, section.start, section.end)
        if not bars:
            cues.append(Cue(section.start, section.end, section.tier, section.tier, palette, support_palette,
                            next_shape()))
            continue

        # Bars at the end of this section that build into the next one's drop
        build_from = section.end
        if next_is_drop and len(bars) >= MIN_BUILD_BARS + 1:
            build_bars = max(MIN_BUILD_BARS, min(MAX_BUILD_BARS, (len(bars) - 1) // 2))
            build_from = bars[-build_bars]

        start = section.start
        if is_drop:
            drop_end = bars[DROP_BARS] if len(bars) > DROP_BARS else section.end
            through = min(1.0, escalation / 3) if partial else escalation / max(len(drops) - 1, 1)
            cue = _drop_cue(start, min(drop_end, build_from), palette, support_palette, escalation, final,
                            through, rng, style, last_effect)
            cues.append(cue)
            last_effect = cue.lead_effect
            start = min(drop_end, build_from)

        # Regular scenes of SCENE_BARS bars up to the build (or the section end)
        scene_starts = [f for f in bars if start <= f < build_from][::SCENE_BARS] or [start]
        scene_starts[0] = start
        for k, scene_start in enumerate(scene_starts):
            scene_end = scene_starts[k + 1] if k + 1 < len(scene_starts) else build_from
            if scene_end <= scene_start:
                continue
            cue = _scene_cue(scene_start, scene_end, section.tier, palette, support_palette, next_shape(),
                             k, style, rng, escalation if section.tier == "peak" else 0, final, last_effect)
            if section.activity < SPARSE:
                _soften(cue, rng, last_effect)
            cues.append(cue)
            last_effect = cue.lead_effect
            if k % 2 == 1:
                # Alternate the supporting palette between scenes too
                support_palette = contrasting(section.tier, palette)

        if build_from < section.end:
            cues.append(_build_cue(build_from, section.end, contrasting("peak", palette), rng, style))
    return cues


def pick(rng, table, avoid=None):
    """Weighted choice from an effect or mode table, rarely repeating `avoid`"""
    names = list(table)
    weights = [table[n] * (0.1 if n == avoid else 1.0) for n in names]
    return rng.choices(names, weights=weights)[0]


def _drop_cue(start, end, palette, support_palette, escalation, final, through, rng, style="mixed", avoid=None):
    """Every strip together on a punchy effect. `through`: 0 for the first drop up
    to 1 for the last, so the biggest moment comes last"""
    lead = {"hit_style": "flash", "hit_source": "beat", "hit_level": 1.0,
            "hit_decay": min(0.5, 0.28 + 0.07 * escalation), "flow_level": 0.9, "flow_beats": 1.0,
            "base_level": 0.04 + 0.03 * escalation, "master": 1.0, "saturation": 1.0}
    support = dict(lead)
    if escalation >= 1:
        support.update({"hit_style": "chase", "hit_size": 0.25, "hit_decay": 0.3})
    if final:
        lead.update({"hit_size": 0.3, "flow_beats": 0.75, "hit_decay": 0.5, "base_level": 0.12})
        support.update({"hit_decay": 0.45, "base_level": 0.1})
    # The last drop gets one of the effects that fill every strip
    table = {"Bloom": 1, "Wipe": 1} if final else EFFECTS["drop"]
    effect = "Freestyle" if style == "freestyle" else pick(rng, table, avoid)
    return Cue(start, end, "drop", "peak", palette, support_palette, "room", lead, support,
               escalation=escalation, final=final, lead_effect=effect, mode="unison", level=0.82 + 0.18 * through)


def _scene_cue(start, end, tier, palette, support_palette, shape, index, style, rng, escalation, final, avoid=None):
    # Freestyle knobs, used when Freestyle is the effect picked
    lead, support = {}, {}
    if tier == "peak":
        lead = {"hit_style": "ripple", "hit_source": "groove"}
        support = {"hit_style": "chase", "hit_source": "beat", "hit_size": 0.15 + 0.05 * escalation, "master": 0.85}
    elif tier == "groove":
        lead = {"hit_style": "block", "hit_source": "groove"}
        support = {"hit_style": "ripple", "hit_source": "snare", "direction": -1, "hit_level": 0.4}
    else:
        lead = {"hit_style": "ripple", "hit_source": "beat", "hit_level": 0.2, "base_level": 0.32, "flow_level": 0.3}
        support = {"flow_level": 0.08, "hit_level": 0.0, "master": 0.6}

    if style == "freestyle":
        effect, mode, support_effects = "Freestyle", "unison" if index % 2 == 0 else "split", []
    else:
        effect = pick(rng, EFFECTS[tier], avoid)
        mode = pick(rng, MODES[tier])
        if mode == "solo" and effect not in EFFECTS["solo"]:
            effect = pick(rng, EFFECTS["solo"], avoid)
        others = [e for e in EFFECTS[tier] if e != effect]
        rng.shuffle(others)
        support_effects = others[:3] if mode == "split" else []
    return Cue(start, end, tier, tier, palette, support_palette, shape, lead, support, support_effects,
               escalation=escalation, final=final, lead_effect=effect, mode=mode,
               solo_step="bar" if tier == "calm" else "beat")


def _soften(cue, rng, avoid=None):
    """Sparse, beatless music: slow flowing colour, no hits on a beat that isn't there"""
    calm = {"hit_level": 0.0, "flow_beats": 6.0, "flow_trail": 2.5, "base_breathe": 0.8, "base_drift": 2.0}
    cue.lead.update(calm, base_level=max(cue.lead.get("base_level", 0.2), 0.25))
    cue.support.update(calm, base_level=0.18, master=0.8)
    cue.lead_effect = pick(rng, EFFECTS["calm"], avoid)
    cue.mode = "solo" if rng.random() < 0.3 else "unison"
    cue.solo_step = "bar"
    cue.support_effects = []
    cue.sparse = True


def _build_cue(start, end, palette, rng=None, style="mixed"):
    effect = "Freestyle" if style == "freestyle" or rng is None else pick(rng, EFFECTS["build"])
    return Cue(start, end, "build", "groove", palette, palette, "mirror",
               lead={"hit_style": "block", "hit_source": "eighth"},
               support={"hit_style": "block", "hit_source": "eighth"}, lead_effect=effect, mode="unison")


def build_targets(cue, progress, beat_seconds, until_drop):
    """Knobs over a build, `progress` 0 at its start to 1 at the drop"""
    last_bar = until_drop is not None and until_drop <= BAR * beat_seconds
    return {
        "flow_beats": 2.0 - 1.75 * progress,
        "flow_level": 0.6 + 0.35 * progress,
        "saturation": 1.0 - 0.8 * progress,
        # Rises out of the dark so the drop still has somewhere to go
        "master": 0.35 + 0.5 * progress,
        "hit_level": 0.4 + 0.5 * progress,
        "hit_size": 0.1 - 0.05 * progress,
        "hit_decay": 0.15 - 0.07 * progress,
        "hit_source": "sixteenth" if last_bar else "eighth",
        "base_level": 0.02,
    }
