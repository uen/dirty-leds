"""Plans the auto show for a pre-analysed track before it plays

A lighting designer doesn't react to a song, they plan it: where the builds
start, what the drops do, how the second drop tops the first. With the whole
track analysed (lib/analysis.py) the show can do the same. plan() turns the
track's sections, drops, beats and grooves into cues, each a stretch of beats
with a scene for the lead strip and the others:

    drop    the first 4 bars after a drop: an impact (white flash and a
            shockwave across the room) on the drop's frame, then every strip
            hitting together on the beat
    peak    the rest of a peak, in 8-bar scenes that alternate how the lead
            and the other strips answer each other
    groove  8-bar scenes; the lead flows and draws the groove, the others
            support it (with fixed effects in "mixed" style)
    calm    dark and breathing; supporting strips off or barely glowing
    build   the bars leading into a drop: flow speeding up, colour draining
            toward white, hits going from eighths to sixteenths, then half a
            beat of darkness before the impact

Drops escalate: each one is bigger than the one before, and the last one
gets the most colourful palette.
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
    "peak": ["Dancefloor", "Spectral", "Sunny", "Fruity", "Jungle"],
}
FINAL_DROP_PALETTE = "Spectral"
SHAPES = ["mirror", "room", "linear"]
# Fixed effects the other strips can use for contrast in "mixed" style
SUPPORT_EFFECTS = {
    "calm": ["Off", "Wavelength"],
    "groove": ["Scroll", "Wavelength", "Bars", "Spectrum", "Energy"],
    "peak": ["Scroll", "Ripple", "Pulse", "Energy"],
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
            cues.append(_drop_cue(start, min(drop_end, build_from), palette, support_palette, escalation, final,
                                  through))
            start = min(drop_end, build_from)

        # Regular scenes of SCENE_BARS bars up to the build (or the section end)
        scene_starts = [f for f in bars if start <= f < build_from][::SCENE_BARS] or [start]
        scene_starts[0] = start
        for k, scene_start in enumerate(scene_starts):
            scene_end = scene_starts[k + 1] if k + 1 < len(scene_starts) else build_from
            if scene_end <= scene_start:
                continue
            cue = _scene_cue(scene_start, scene_end, section.tier, palette, support_palette, next_shape(),
                             k, style, rng, escalation if section.tier == "peak" else 0, final)
            if section.activity < SPARSE:
                _soften(cue)
            cues.append(cue)
            if k % 2 == 1:
                # Alternate the supporting palette between scenes too
                support_palette = contrasting(section.tier, palette)

        if build_from < section.end:
            cues.append(_build_cue(build_from, section.end, contrasting("peak", palette)))
    return cues


def _drop_cue(start, end, palette, support_palette, escalation, final, through):
    """`through`: 0 for the first drop up to 1 for the last, so the biggest moment comes last"""
    # Each drop hits a little harder and longer than the one before
    lead = {"hit_style": "flash", "hit_source": "beat", "hit_level": 1.0,
            "hit_decay": min(0.5, 0.28 + 0.07 * escalation), "flow_level": 0.9, "flow_beats": 1.0,
            "base_level": 0.04 + 0.03 * escalation, "master": 0.82 + 0.18 * through, "saturation": 1.0}
    support = dict(lead)
    if escalation >= 1:
        # Later drops: the others chase around the room instead of copying the lead
        support.update({"hit_style": "chase", "hit_size": 0.25, "hit_decay": 0.3})
    if final:
        lead.update({"hit_size": 0.3, "flow_beats": 0.75, "hit_decay": 0.5, "base_level": 0.12})
        support.update({"hit_decay": 0.45, "base_level": 0.1})
    return Cue(start, end, "drop", "peak", palette, support_palette, "room", lead, support,
               escalation=escalation, final=final)


def _scene_cue(start, end, tier, palette, support_palette, shape, index, style, rng, escalation, final):
    lead, support, support_effects = {}, {}, []
    if tier == "peak":
        if index % 2 == 0:
            lead = {"hit_style": "ripple", "hit_source": "groove"}
            support = {"hit_style": "chase", "hit_source": "beat", "hit_size": 0.15 + 0.05 * escalation,
                       "master": 0.85}
        else:
            lead = {"hit_style": "block", "hit_source": "groove", "hit_size": 0.12}
            support = {"hit_style": "ripple", "hit_source": "snare", "direction": -1, "master": 0.85}
        if final:
            lead.update({"hit_level": 1.0, "flow_beats": 0.75})
    elif tier == "groove":
        lead = {"hit_style": "block", "hit_source": "groove"}
        support = {"hit_style": "ripple", "hit_source": "snare", "direction": -1, "hit_level": 0.4}
    else:
        # Calm parts glow gently rather than going dead: the lead keeps a breathing colour field
        lead = {"hit_style": "ripple", "hit_source": "beat", "hit_level": 0.2, "base_level": 0.32, "flow_level": 0.3}
        support = {"flow_level": 0.08, "hit_level": 0.0, "master": 0.6}
    if style == "mixed" and tier != "peak" or (style == "mixed" and index % 2 == 1):
        support_effects = rng.sample(SUPPORT_EFFECTS[tier], k=min(3, len(SUPPORT_EFFECTS[tier])))
    return Cue(start, end, tier, tier, palette, support_palette, shape, lead, support, support_effects,
               escalation=escalation, final=final)


def _soften(cue):
    """Sparse, beatless music: slow flowing colour, no hits on a beat that isn't there"""
    calm = {"hit_level": 0.0, "flow_beats": 6.0, "flow_trail": 2.5, "base_breathe": 0.8, "base_drift": 2.0}
    cue.lead.update(calm, base_level=max(cue.lead.get("base_level", 0.2), 0.25))
    cue.support.update(calm, base_level=0.18, master=0.8)
    # Every strip on its own slowly evolving colour field rather than fixed effects
    cue.support_effects = []
    cue.sparse = True


def _build_cue(start, end, palette):
    return Cue(start, end, "build", "groove", palette, palette, "mirror",
               lead={"hit_style": "block", "hit_source": "eighth"},
               support={"hit_style": "block", "hit_source": "eighth"})


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
