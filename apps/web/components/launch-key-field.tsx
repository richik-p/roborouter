"use client";

import { KeyRound } from "lucide-react";
import { useSyncExternalStore } from "react";
import { getLaunchKey, setLaunchKey, subscribeLaunchKey } from "@/lib/launch-key";

export default function LaunchKeyField() {
  const value = useSyncExternalStore(subscribeLaunchKey, getLaunchKey, () => "");
  return (
    <div className="field launch-key">
      <label htmlFor="launch-key"><KeyRound size={11} /> Access key</label>
      <input
        id="launch-key"
        type="password"
        autoComplete="off"
        spellCheck={false}
        placeholder="rrl_… (issued per beta user)"
        value={value}
        onChange={(event) => setLaunchKey(event.target.value.trim())}
      />
    </div>
  );
}
