import { useRef } from "react";
import type { AudioSource, State } from "../api";
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
      <Spectrum frames={frames} />
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
                  <span className="cue-label">{source.label.replace(/^test \/ /, "")}</span>
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
