import type { State } from "../api";
import type { RunAction } from "../hooks/useLedApp";
import { Profiles } from "./Profiles";
import { Slider } from "./Slider";

interface HeaderProps {
  state: State | null;
  connected: boolean;
  error: string | null;
  run: RunAction;
}

export function Header({ state, connected, error, run }: HeaderProps) {
  const status = (
    <p className="status" data-connected={connected}>
      {connected ? "Live" : "Reconnecting to the LED app…"}
    </p>
  );

  if (!state) {
    return (
      <header className="panel header">
        <div className="title"><h1 className="room-name">dirty-leds</h1>{status}</div>
      </header>
    );
  }

  return (
    <header className="panel header">
      <div className="title">
        <h1 className="room-name">{state.room?.name ?? "Your room"}</h1>
        {status}
      </div>
      <Slider
        className="master"
        label="Master"
        value={state.brightness}
        min={0}
        max={100}
        step={1}
        format={(v) => `${v}%`}
        onChange={(value) => run("set-brightness", { value })}
      />
      <label className="toggle">
        <input type="checkbox" checked={state.sync} onChange={(e) => run("set-sync", { value: e.target.checked })} />
        <span>Sync strips</span>
      </label>
      <Profiles state={state} run={run} />
      {error && <p className="error" role="alert">{error}</p>}
    </header>
  );
}
