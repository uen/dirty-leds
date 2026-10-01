import { useCallback, useEffect, useMemo, useState } from "react";
import { action, connect, type State } from "../api";
import { FrameBus } from "../frames";

export type RunAction = (name: string, payload: Record<string, unknown>) => void;

/** Connection to the Python app: live state, LED frames and a way to run actions */
export function useLedApp() {
  const [state, setState] = useState<State | null>(null);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const frames = useMemo(() => new FrameBus(), []);

  useEffect(() => {
    const events = connect({
      onState: setState,
      onConnection: setConnected,
      onFrame: (frame) => frames.emit(frame),
    });
    return () => events.close();
  }, [frames]);

  // The resulting state change arrives over the event stream
  const run: RunAction = useCallback((name, payload) => {
    action(name, payload).then(setError);
  }, []);

  return { state, connected, error, run, frames };
}
