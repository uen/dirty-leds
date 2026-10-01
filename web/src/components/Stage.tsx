import { useEffect, useRef, useState } from "react";
import type { State } from "../api";
import { useFrame, type FrameBus } from "../frames";
import { RoomView } from "../RoomView";

/** The 3D room. RoomView is imperative three.js; this component only mounts it and feeds it */
export function Stage({ state, frames }: { state: State | null; frames: FrameBus }) {
  const container = useRef<HTMLDivElement>(null);
  const view = useRef<RoomView | null>(null);
  // Low by default: in a dark room the strips should do the lighting
  const [roomLight, setRoomLight] = useState(0.1);
  const [ledBrightness, setLedBrightness] = useState(1);

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
  useEffect(() => view.current?.setLedBrightness(ledBrightness), [ledBrightness]);

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
        <label>
          <span className="control-label">LED brightness</span>
          <input type="range" min={0.1} max={3} step={0.1} value={ledBrightness}
            onChange={(e) => setLedBrightness(Number(e.target.value))} />
        </label>
      </div>
    </main>
  );
}
