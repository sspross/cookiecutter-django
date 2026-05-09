import { useEffect, useState } from "react";
import { Monitor, Moon, Sun } from "@/components/layout/icons";
import { cn } from "@/lib/utils";

type Mode = "system" | "light" | "dark";

const STORAGE_KEY = "app-color-mode";

function readStored(): Mode {
  if (typeof localStorage === "undefined") return "system";
  const v = localStorage.getItem(STORAGE_KEY);
  return v === "light" || v === "dark" || v === "system" ? v : "system";
}

function applyMode(mode: Mode) {
  const isDark =
    mode === "dark" ||
    (mode === "system" && window.matchMedia("(prefers-color-scheme: dark)").matches);
  document.documentElement.classList.toggle("dark", isDark);
}

export function ThemeToggle() {
  const [mode, setMode] = useState<Mode>(() => readStored());

  useEffect(() => {
    applyMode(mode);
    if (mode === "system" && typeof window !== "undefined") {
      const mq = window.matchMedia("(prefers-color-scheme: dark)");
      const handler = () => applyMode("system");
      mq.addEventListener("change", handler);
      return () => mq.removeEventListener("change", handler);
    }
  }, [mode]);

  function pick(next: Mode) {
    setMode(next);
    localStorage.setItem(STORAGE_KEY, next);
  }

  const buttons: { value: Mode; Icon: typeof Sun; label: string }[] = [
    { value: "system", Icon: Monitor, label: "System" },
    { value: "light", Icon: Sun, label: "Light" },
    { value: "dark", Icon: Moon, label: "Dark" },
  ];
  return (
    <div
      role="radiogroup"
      aria-label="Color mode"
      className="inline-flex overflow-hidden rounded-md border border-border"
    >
      {buttons.map(({ value, Icon, label }) => (
        <button
          key={value}
          type="button"
          aria-label={label}
          aria-checked={mode === value}
          role="radio"
          onClick={() => pick(value)}
          className={cn(
            "flex h-6 w-6 items-center justify-center text-muted-foreground hover:text-foreground",
            mode === value && "bg-accent text-foreground",
          )}
        >
          <Icon className="h-3.5 w-3.5" />
        </button>
      ))}
    </div>
  );
}
