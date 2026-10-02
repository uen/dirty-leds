import { useRef } from "react";
import type { Device } from "../api";
import { averageColour, cssRgb } from "../colour";
import { useFrame, type FrameBus } from "../frames";

interface ChannelsProps {
  devices: Device[];
  selected: string | null;
  onSelect: (device: string) => void;
  frames: FrameBus;
}

/** One console channel per strip, with a swatch showing the strip's live average colour */
export function Channels({ devices, selected, onSelect, frames }: ChannelsProps) {
  return (
    <section className="channels" aria-label="Strips">
      {devices.map((device) => (
        <Channel key={device.name} device={device} selected={device.name === selected}
          onSelect={() => onSelect(device.name)} frames={frames} />
      ))}
    </section>
  );
}

interface ChannelProps {
  device: Device;
  selected: boolean;
  onSelect: () => void;
  frames: FrameBus;
}

function Channel({ device, selected, onSelect, frames }: ChannelProps) {
  const swatch = useRef<HTMLSpanElement>(null);

  useFrame(frames, ({ leds }) => {
    const bytes = leds[device.name];
    if (bytes && swatch.current) swatch.current.style.setProperty("--live", cssRgb(averageColour(bytes)));
  });

  return (
    <button className="channel" aria-pressed={selected} onClick={onSelect}>
      <span ref={swatch} className="swatch" aria-hidden="true" />
      <span className="channel-name">{device.name}</span>
      <span className="channel-effect">
        {device.currentEffect === "Auto" && device.showing ? `Auto: ${device.showing}` : device.currentEffect}
      </span>
      <span className="channel-meta">{device.leds} LEDs</span>
    </button>
  );
}
