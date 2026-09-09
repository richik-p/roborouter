// Beta launch key, kept per browser. Exposed as a tiny external store so React reads it
// without effects and without a server/client hydration mismatch.
const STORAGE_KEY = "roborouter.launch_key";
const listeners = new Set<() => void>();
let current: string | null = null;

function read(): string {
  try {
    return window.localStorage.getItem(STORAGE_KEY) ?? "";
  } catch {
    return "";
  }
}

export function getLaunchKey(): string {
  if (typeof window === "undefined") return "";
  if (current === null) current = read();
  return current;
}

export function setLaunchKey(value: string): void {
  current = value;
  try {
    if (value) window.localStorage.setItem(STORAGE_KEY, value);
    else window.localStorage.removeItem(STORAGE_KEY);
  } catch {
    // Storage can be unavailable (private mode, blocked site data); the key then lives for the page only.
  }
  for (const listener of listeners) listener();
}

export function subscribeLaunchKey(listener: () => void): () => void {
  listeners.add(listener);
  const onStorage = (event: StorageEvent) => {
    if (event.key === STORAGE_KEY) {
      current = null;
      listener();
    }
  };
  window.addEventListener("storage", onStorage);
  return () => {
    listeners.delete(listener);
    window.removeEventListener("storage", onStorage);
  };
}

export function launchHeaders(): Record<string, string> {
  const key = getLaunchKey();
  return key ? { Authorization: `Bearer ${key}` } : {};
}
