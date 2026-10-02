import { useRef } from "react";
import type { Analysis, AudioSource, State } from "../api";
import { useFrame, type FrameBus } from "../frames";
import type { RunAction } from "../hooks/useLedApp";

const TEST_TRACK_PREFIX = "track:test/";

/** Cue list of audio sources: live inputs, generated test tracks and the user's music */
export function SoundPanel({ audio, run, frames }: { audio: State["audio"] | undefined; run: RunAction; frames: FrameBus }) {
  const sources = audio?.sources ?? [];
  const live = sources.filter((s) => s.kind === "live" && s.id !== "off");
  const tests = sources.filter((s) => s.id.startsWith(TEST_TRACK_PREFIX));
  const music = sources.filter((s) => s.kind === "track" && !s.id.startsWith(TEST_TRACK_PREFIX));
  const current = audio?.source ?? "off";
  const play = (source: AudioSource) => run("set-audio", { source: source.id === current ? "off" : source.id });

  return (
    <aside className="panel sound">
      <h2>Sound</h2>
      {audio && <ShowMode analysis={audio.analysis} frames={frames} />}
      <Spectrum frames={frames} />
      <Meters frames={frames} />
      <div className="cues">
        {audio?.error && <p className="error" role="alert">{audio.error}</p>}
        <CueGroup title="Live input" sources={live} current={current} onPlay={play} />
        <CueGroup title="Test tracks" sources={tests} current={current} onPlay={play} />
        <CueGroup title="Your music" sources={music} current={current} onPlay={play}
          empty="Add audio files to python/music to play them here." />
      </div>
    </aside>
  );
}

interface CueGroupProps {
  title: string;
  sources: AudioSource[];
  current: string;
  onPlay: (source: AudioSource) => void;
  empty?: string;
}

function CueGroup({ title, sources, current, onPlay, empty }: CueGroupProps) {
  if (!sources.length && !empty) return null;
  return (
    <section>
      <h3>{title}</h3>
      {sources.length ? (
        <ul>
          {sources.map((source) => {
            const active = source.id === current;
            return (
              <li key={source.id}>
                <button className="cue" aria-pressed={active} onClick={() => onPlay(source)}>
                  <span className="cue-label">
                    {source.label.replace(/^test \/ /, "")}
                    {source.analysed && <span className="cue-tag" title="Pre-analysed: the show can see what's coming">mapped</span>}
                  </span>
                  <span className="cue-state">{active ? (source.kind === "track" ? "Stop" : "On") : ""}</span>
                </button>
              </li>
            );
          })}
        </ul>
      ) : (
        <p className="hint">{empty}</p>
      )}
    </section>
  );
}

/** Says whether the show is reacting live or following a pre-analysed map of the track */
function ShowMode({ analysis, frames }: { analysis: Analysis; frames: FrameBus }) {
  switch (analysis.status) {
    case "ready":
      return (
        <div className="show-mode" data-mode="ready">
          <p><strong>Pre-analysed.</strong> {analysis.tempo} bpm, {analysis.drops?.length ?? 0} drops. The show sees what's coming.</p>
          <TrackMap analysis={analysis} frames={frames} />
          <Upcoming frames={frames} />
          {analysis.groove?.reliable && <GroovePattern groove={analysis.groove} frames={frames} />}
        </div>
      );
    case "queued":
    case "analysing":
      return (
        <p className="show-mode" data-mode="analysing">
          <strong>Analysing this track{analysis.status === "analysing" ? `, ${Math.round((analysis.progress ?? 0) * 100)}%` : ""}.</strong>{" "}
          Reacting live until it's ready.
        </p>
      );
    case "failed":
      return (
        <p className="show-mode" data-mode="failed">
          <strong>Couldn't analyse this track</strong> ({analysis.error}). Reacting live.
        </p>
      );
    default:
      return (
        <p className="show-mode" data-mode="live">
          <strong>Live.</strong> Reacting as it hears, with no lookahead. Tracks from your music get pre-analysed.
        </p>
      );
  }
}

/** The track's sections coloured by energy, drops marked, with a playhead */
function TrackMap({ analysis, frames }: { analysis: Analysis; frames: FrameBus }) {
  const playhead = useRef<HTMLSpanElement>(null);
  const duration = analysis.duration ?? 1;

  useFrame(frames, ({ position }) => {
    if (playhead.current && position !== null) {
      playhead.current.style.left = `${Math.min(100, (100 * position) / duration)}%`;
    }
  });

  return (
    <div className="track-map" role="img" aria-label="Sections of the track by energy, with drops marked">
      {analysis.sections?.map((section) => (
        <span key={section.start} className="track-section" data-tier={section.tier}
          style={{ left: `${(100 * section.start) / duration}%`, width: `${(100 * (section.end - section.start)) / duration}%` }} />
      ))}
      {analysis.drops?.map((drop) => (
        <span key={drop} className="track-drop" style={{ left: `${(100 * drop) / duration}%` }} />
      ))}
      <span ref={playhead} className="track-playhead" />
    </div>
  );
}

const NEXT_NAMES = { calm: "Breakdown", groove: "Groove", peak: "Peak" } as const;

/** Countdown to the next section of the track */
function Upcoming({ frames }: { frames: FrameBus }) {
  const text = useRef<HTMLParagraphElement>(null);
  useFrame(frames, ({ upcoming }) => {
    if (!text.current) return;
    text.current.textContent = upcoming
      ? `${upcoming.drop ? "Drop" : NEXT_NAMES[upcoming.tier]} in ${upcoming.in.toFixed(1)} s`
      : "Last section";
    text.current.dataset.soon = String(Boolean(upcoming && upcoming.drop && upcoming.in < 5));
  });
  return <p ref={text} className="upcoming" aria-live="off" />;
}

/** The song's repeating rhythm as 16 steps, the current one lit */
function GroovePattern({ groove, frames }: { groove: NonNullable<Analysis["groove"]>; frames: FrameBus }) {
  const dots = useRef<(HTMLSpanElement | null)[]>([]);
  const lit = useRef(-1);
  useFrame(frames, ({ step }) => {
    if (step === lit.current) return;
    dots.current[lit.current]?.classList.remove("step-on");
    dots.current[step]?.classList.add("step-on");
    lit.current = step;
  });
  return (
    <div className="groove" title={`Repeating rhythm, ${Math.round(groove.strength * 100)}% consistent`}>
      <span className="control-label">Groove</span>
      <span className="groove-steps">
        {groove.pattern.map((level, i) => (
          <span
            key={i}
            ref={(el) => { dots.current[i] = el; }}
            className="groove-step"
            data-accent={groove.accents.includes(i)}
            data-beat={i % 4 === 0}
            style={{ opacity: 0.25 + 0.75 * level }}
          />
        ))}
      </span>
    </div>
  );
}

const METERS = [
  ["bass", "Bass"],
  ["mid", "Mids"],
  ["treble", "Treble"],
  ["intensity", "Intensity"],
] as const;

/** What the effects are reacting to: band levels, how big the song is, tempo and beats */
function Meters({ frames }: { frames: FrameBus }) {
  const bars = useRef<Record<string, HTMLSpanElement | null>>({});
  const tempo = useRef<HTMLSpanElement>(null);
  const beat = useRef<HTMLSpanElement>(null);
  const lastBeats = useRef(0);

  useFrame(frames, ({ meters, tempo: bpm, beats }) => {
    for (const [key] of METERS) bars.current[key]?.style.setProperty("--level", String(meters?.[key] ?? 0));
    if (tempo.current) tempo.current.textContent = bpm ? `${Math.round(bpm)} bpm` : "";
    if (beats !== lastBeats.current && beat.current) {
      lastBeats.current = beats;
      // Restart the flash animation
      beat.current.classList.remove("beat-on");
      void beat.current.offsetWidth;
      beat.current.classList.add("beat-on");
    }
  });

  return (
    <div className="meters">
      {METERS.map(([key, label]) => (
        <div key={key} className="meter">
          <span className="control-label">{label}</span>
          <span className="meter-track"><span ref={(el) => { bars.current[key] = el; }} className="meter-fill" /></span>
        </div>
      ))}
      <div className="tempo">
        <span ref={beat} className="beat-dot" aria-hidden="true" />
        <span ref={tempo} className="readout" />
      </div>
    </div>
  );
}

function Spectrum({ frames }: { frames: FrameBus }) {
  const canvas = useRef<HTMLCanvasElement>(null);

  useFrame(frames, ({ spectrum }) => {
    const context = canvas.current?.getContext("2d");
    if (!context || !canvas.current) return;
    const { width, height } = canvas.current;
    context.clearRect(0, 0, width, height);
    if (!spectrum.length) return;
    const gap = 2;
    const barWidth = (width - gap * (spectrum.length - 1)) / spectrum.length;
    context.fillStyle = "#ffb547";
    spectrum.forEach((value, i) => {
      const barHeight = Math.max(1, Math.min(1, value) * height);
      context.fillRect(i * (barWidth + gap), height - barHeight, barWidth, barHeight);
    });
  });

  return <canvas ref={canvas} className="spectrum" width={240} height={56} aria-hidden="true" />;
}
