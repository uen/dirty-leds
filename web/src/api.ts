// Shapes returned by python/lib/api.py get_state() and the /api/events stream

export type Vec3 = [number, number, number];

export interface EffectOption {
  key: string;
  label: string;
  type: "slider" | "float_slider" | "checkbox" | "dropdown";
  config: [number, number, number] | string[] | null;
}

export interface Effect {
  name: string;
  reactive: boolean;
  options: EffectOption[];
  values: Record<string, number | boolean | string>;
}

export interface Device {
  name: string;
  leds: number;
  currentEffect: string;
  /** The effect the auto show picked, while currentEffect is "Auto" */
  showing: string | null;
  minFrequency: number;
  maxFrequency: number;
  layout: Vec3[] | null;
  effects: Effect[];
}

export interface AudioSource {
  id: string;
  label: string;
  kind: "live" | "track";
}

export interface Furniture {
  label: string;
  kind: "box" | "screen" | "window";
  pos: Vec3;
  size: Vec3;
  color: string;
}

export interface Room {
  name: string;
  size: Vec3;
  furniture: Furniture[];
}

export interface State {
  /** Every strip is on the auto show */
  autoShow: boolean;
  sync: boolean;
  brightness: number;
  currentProfile: string;
  profiles: { id: string; name: string }[];
  audio: { source: string; error: string | null; sources: AudioSource[] };
  room: Room | null;
  devices: Device[];
}

export interface Frame {
  leds: Record<string, Uint8Array>;
  /** 24 log-spaced bands, 0-1, each against its own recent range */
  spectrum: number[];
  meters: Record<"bass" | "mid" | "treble" | "intensity", number>;
  tempo: number;
  /** Running beat count; a change means a beat landed */
  beats: number;
}

export async function action(name: string, payload: Record<string, unknown>): Promise<string | null> {
  const response = await fetch("/api/action", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action: name, payload }),
  });
  if (response.ok) return null;
  const body = await response.json().catch(() => ({ error: response.statusText }));
  return body.error ?? "Request failed";
}

function decodeBase64(data: string): Uint8Array {
  const binary = atob(data);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  return bytes;
}

export function connect(handlers: {
  onState: (state: State) => void;
  onFrame: (frame: Frame) => void;
  onConnection: (connected: boolean) => void;
}): EventSource {
  const events = new EventSource("/api/events");
  events.addEventListener("open", () => handlers.onConnection(true));
  events.addEventListener("error", () => handlers.onConnection(false));
  events.addEventListener("state", (event) => handlers.onState(JSON.parse((event as MessageEvent).data)));
  events.addEventListener("frame", (event) => {
    const data = JSON.parse((event as MessageEvent).data);
    const leds: Record<string, Uint8Array> = {};
    for (const [name, encoded] of Object.entries<string>(data.leds)) leds[name] = decodeBase64(encoded);
    handlers.onFrame({ leds, spectrum: data.spectrum, meters: data.meters, tempo: data.tempo, beats: data.beats });
  });
  return events;
}
