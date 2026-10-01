import { useState } from "react";
import { Channels } from "./components/Channels";
import { EffectsPanel } from "./components/EffectsPanel";
import { Header } from "./components/Header";
import { SoundPanel } from "./components/SoundPanel";
import { Stage } from "./components/Stage";
import { useLedApp } from "./hooks/useLedApp";

export function App() {
  const { state, connected, error, run, frames } = useLedApp();
  const [selected, setSelected] = useState<string | null>(null);

  const devices = state?.devices ?? [];
  const device = devices.find((d) => d.name === selected) ?? devices[0];

  return (
    <div className="console">
      <Header state={state} connected={connected} error={error} run={run} />
      <Stage state={state} frames={frames} />
      <SoundPanel audio={state?.audio} run={run} frames={frames} />
      <Channels devices={devices} selected={device?.name ?? null} onSelect={setSelected} frames={frames} />
      <EffectsPanel device={device} synced={Boolean(state?.sync && devices.length > 1)} run={run} />
    </div>
  );
}
