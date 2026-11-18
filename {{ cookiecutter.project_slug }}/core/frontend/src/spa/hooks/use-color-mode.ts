import { useEffect, useState } from "react";

export type ColorMode = "system" | "light" | "dark";

const STORAGE_KEY = "app-color-mode";
const SYSTEM_DARK_QUERY = "(prefers-color-scheme: dark)";

function readStored(): ColorMode {
  const stored = localStorage.getItem(STORAGE_KEY);
  return stored === "light" || stored === "dark" || stored === "system"
    ? stored
    : "system";
}

function applyToDocument(mode: ColorMode) {
  const isDark =
    mode === "dark" ||
    (mode === "system" && window.matchMedia(SYSTEM_DARK_QUERY).matches);
  document.documentElement.classList.toggle("dark", isDark);
}

export function useColorMode(): [ColorMode, (next: ColorMode) => void] {
  const [mode, setMode] = useState<ColorMode>(readStored);

  useEffect(() => {
    applyToDocument(mode);
    if (mode !== "system") return;
    const systemDark = window.matchMedia(SYSTEM_DARK_QUERY);
    const followSystem = () => applyToDocument("system");
    systemDark.addEventListener("change", followSystem);
    return () => systemDark.removeEventListener("change", followSystem);
  }, [mode]);

  function pick(next: ColorMode) {
    setMode(next);
    localStorage.setItem(STORAGE_KEY, next);
  }

  return [mode, pick];
}
