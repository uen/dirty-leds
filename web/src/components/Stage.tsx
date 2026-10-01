import { useEffect, useRef } from "react";
import type { State } from "../api";
import { useFrame, type FrameBus } from "../frames";
import { RoomView } from "../RoomView";

/** The 3D room. RoomView is imperative three.js; this component only mounts it and feeds it */
export function Stage({ state, frames }: { state: State | null; frames: FrameBus }) {
  const container = useRef<HTMLElement>(null);
  const view = useRef<RoomView | null>(null);

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

  useFrame(frames, (frame) => view.current?.setFrame(frame.leds));

  return <main ref={container} className="stage" aria-label="3D view of the room and its LED strips" />;
}
