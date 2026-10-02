import type { Device, Effect, EffectOption } from "../api";
import type { RunAction } from "../hooks/useLedApp";
import { Slider } from "./Slider";

interface EffectsPanelProps {
  device: Device | undefined;
  synced: boolean;
  run: RunAction;
}

/** Effect picker and settings for the selected strip */
export function EffectsPanel({ device, synced, run }: EffectsPanelProps) {
  if (!device) return <section className="panel effects" />;

  const current = device.effects.find((e) => e.name === device.currentEffect);
  const pick = (effect: Effect) => run("set-effect", { device: device.name, effect: effect.name });

  return (
    <section className="panel effects" aria-label={`Effects for ${device.name}`}>
      <header className="effects-header">
        <h2>{device.name}</h2>
        {synced && <p className="hint">Sync is on, so changes apply to every strip.</p>}
        {device.currentEffect === "Auto" && (
          <p className="hint">
            The auto show is choosing effects for this strip{device.showing ? `, now ${device.showing}` : ""}.
            Pick any effect to take over.
          </p>
        )}
      </header>
      <EffectList title="Follows the music" effects={device.effects.filter((e) => e.reactive)}
        current={device.currentEffect} onPick={pick} />
      <EffectList title="Ambient" effects={device.effects.filter((e) => !e.reactive)}
        current={device.currentEffect} onPick={pick} />
      {current && current.options.length > 0 && (
        <section className="options">
          <h3>{current.name} settings</h3>
          <div className="option-grid">
            {current.options.map((option) => (
              <OptionControl
                key={`${current.name}/${option.key}`}
                option={option}
                value={current.values[option.key]}
                onChange={(value) =>
                  run("set-option", { device: device.name, effect: current.name, option: option.key, value })}
              />
            ))}
          </div>
        </section>
      )}
    </section>
  );
}

interface EffectListProps {
  title: string;
  effects: Effect[];
  current: string;
  onPick: (effect: Effect) => void;
}

function EffectList({ title, effects, current, onPick }: EffectListProps) {
  return (
    <section>
      <h3>{title}</h3>
      <ul className="effect-list">
        {effects.map((effect) => (
          <li key={effect.name}>
            <button className="effect" aria-pressed={effect.name === current} onClick={() => onPick(effect)}>
              {effect.name}
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}

interface OptionControlProps {
  option: EffectOption;
  value: number | boolean | string | undefined;
  onChange: (value: number | boolean | string) => void;
}

function OptionControl({ option, value, onChange }: OptionControlProps) {
  if (option.type === "checkbox") {
    return (
      <label className="toggle">
        <input type="checkbox" checked={Boolean(value)} onChange={(e) => onChange(e.target.checked)} />
        <span>{option.label}</span>
      </label>
    );
  }

  if (option.type === "dropdown") {
    const choices = (option.config as string[] | null) ?? [];
    return (
      <label className="field">
        <span className="control-label">{option.label}</span>
        <select value={String(value)} onChange={(e) => onChange(e.target.value)}>
          {choices.map((choice) => <option key={choice} value={choice}>{choice}</option>)}
        </select>
      </label>
    );
  }

  const [min, max, step] = (option.config as [number, number, number] | null) ?? [0, 1, 0.01];
  return (
    <Slider label={option.label} value={Number(value)} min={min} max={max} step={step}
      format={formatNumber} onChange={onChange} />
  );
}

function formatNumber(value: number): string {
  if (Number.isInteger(value)) return String(value);
  return value.toFixed(Math.abs(value) < 0.01 ? 4 : 2);
}
