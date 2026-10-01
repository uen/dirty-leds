import { useEffect, useRef } from "react";
import type { Frame } from "./api";

type FrameListener = (frame: Frame) => void;

/** Delivers LED frames outside React state, so 60 fps updates don't re-render components */
export class FrameBus {
  private listeners = new Set<FrameListener>();

  subscribe(listener: FrameListener): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  emit(frame: Frame) {
    for (const listener of this.listeners) listener(frame);
  }
}

/** Runs `callback` for every frame, always calling the latest version of it */
export function useFrame(bus: FrameBus, callback: FrameListener) {
  const latest = useRef(callback);
  useEffect(() => {
    latest.current = callback;
  });
  useEffect(() => bus.subscribe((frame) => latest.current(frame)), [bus]);
}
