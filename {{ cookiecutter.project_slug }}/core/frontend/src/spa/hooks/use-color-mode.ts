import { useSyncExternalStore } from "react";

export type ColorMode = "system" | "light" | "dark";

const STORAGE_KEY = "app-color-mode";
const SYSTEM_DARK_QUERY = "(prefers-color-scheme: dark)";

const systemDark = window.matchMedia(SYSTEM_DARK_QUERY);
const subscribers = new Set<() => void>();

function readStored(): ColorMode {
  const stored = localStorage.getItem(STORAGE_KEY);
  return stored === "light" || stored === "dark" || stored === "system"
    ? stored
    : "system";
}

function applyStoredToDocument() {
  const mode = readStored();
  const isDark = mode === "dark" || (mode === "system" && systemDark.matches);
  document.documentElement.classList.toggle("dark", isDark);
}

function subscribe(rerender: () => void) {
  if (subscribers.size === 0) {
    applyStoredToDocument();
    systemDark.addEventListener("change", applyStoredToDocument);
  }
  subscribers.add(rerender);
  return () => {
    subscribers.delete(rerender);
    if (subscribers.size === 0) {
      systemDark.removeEventListener("change", applyStoredToDocument);
    }
  };
}

function pick(next: ColorMode) {
  localStorage.setItem(STORAGE_KEY, next);
  applyStoredToDocument();
  for (const rerender of subscribers) rerender();
}

export function useColorMode(): [ColorMode, (next: ColorMode) => void] {
  return [useSyncExternalStore(subscribe, readStored), pick];
}
