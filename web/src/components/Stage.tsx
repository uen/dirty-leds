import { useEffect, useRef, useState } from "react";
import type { State } from "../api";
import type { RunAction } from "../hooks/useLedApp";
import { useFrame, type FrameBus } from "../frames";
import { RoomView } from "../RoomView";
import { Slider } from "./Slider";

/** The 3D room. RoomView is imperative three.js; this component only mounts it and feeds it */
export function Stage({ state, frames, run }: { state: State | null; frames: FrameBus; run: RunAction }) {
  const container = useRef<HTMLDivElement>(null);
  const view = useRef<RoomView | null>(null);
  // Low by default: in a dark room the strips should do the lighting
  const [roomLight, setRoomLight] = useState(0.1);

  useEffect(() => {
    view.current = new RoomView(container.current!);
    return () => {
      view.current?.dispose();
      view.current = null;
    };
  }, []);

  useEffect(() => {
    if (state) view.current?.setLayout(state.room, state.devices);
  }, [state]);

  useEffect(() => view.current?.setRoomLight(roomLight), [roomLight]);

  useFrame(frames, (frame) => view.current?.setFrame(frame.leds));

  return (
    <main className="stage" aria-label="3D view of the room and its LED strips">
      <div ref={container} className="stage-canvas" />
      <div className="view-controls">
        <label>
          <span className="control-label">Room light</span>
          <input type="range" min={0} max={1} step={0.05} value={roomLight}
            onChange={(e) => setRoomLight(Number(e.target.value))} />
        </label>
        {/* the real strips' brightness (same as Master): the room shows what they send */}
        {state && (
          <Slider
            className=""
            label="LED brightness"
            value={state.brightness}
            min={0}
            max={100}
            step={1}
            format={(v) => `${v}%`}
            onChange={(value) => run("set-brightness", { value })}
          />
        )}
      </div>
    </main>
  );
}
