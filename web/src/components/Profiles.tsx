import { useState } from "react";
import type { State } from "../api";
import type { RunAction } from "../hooks/useLedApp";

export function Profiles({ state, run }: { state: State; run: RunAction }) {
  const [name, setName] = useState("");

  return (
    <div className="profiles">
      <select
        aria-label="Profile"
        value={state.currentProfile}
        onChange={(e) => e.target.value && run("load-profile", { id: e.target.value })}
      >
        <option value="">Unsaved setup</option>
        {state.profiles.map((p) => (
          <option key={p.id} value={p.id}>{p.name ?? p.id}</option>
        ))}
      </select>
      {state.currentProfile && (
        <button className="quiet" onClick={() => run("delete-profile", { id: state.currentProfile })}>Delete</button>
      )}
      <form
        className="profile-save"
        onSubmit={(e) => {
          e.preventDefault();
          if (!name.trim()) return;
          run("save-profile", { name });
          setName("");
        }}
      >
        <input type="text" placeholder="Profile name" maxLength={40} aria-label="Profile name"
          value={name} onChange={(e) => setName(e.target.value)} />
        <button type="submit">Save</button>
      </form>
    </div>
  );
}
