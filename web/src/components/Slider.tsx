import { useEffect, useMemo, useRef, useState } from "react";
import { throttle } from "../throttle";

interface SliderProps {
  label: string;
  value: number;
  min: number;
  max: number;
  step?: number;
  format?: (value: number) => string;
  onChange: (value: number) => void;
  className?: string;
}

/** Range input that holds its own value while dragged and sends throttled updates */
export function Slider({ label, value, min, max, step, format = String, onChange, className = "field" }: SliderProps) {
  const [draft, setDraft] = useState<number | null>(null);
  const latestOnChange = useRef(onChange);
  useEffect(() => {
    latestOnChange.current = onChange;
  });
  const send = useMemo(() => throttle((v: number) => latestOnChange.current(v), 80), []);

  const shown = draft ?? value;
  return (
    <label className={className}>
      <span className="control-label">{label}</span>
      <input
        type="range"
        min={min}
        max={max}
        step={step || "any"}
        value={shown}
        onChange={(e) => {
          const v = Number(e.target.value);
          setDraft(v);
          send(v);
        }}
        onPointerUp={() => setDraft(null)}
        onBlur={() => setDraft(null)}
      />
      <output className="readout">{format(shown)}</output>
    </label>
  );
}
