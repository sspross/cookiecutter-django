import { useEffect, useId, useState } from "react";
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
  // The shell renders this twice (sidebar and mobile nav); a shared radio
  // name would fuse both into one browser-level group.
  const groupName = useId();

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

  const options: { value: Mode; Icon: typeof Sun; label: string }[] = [
    { value: "system", Icon: Monitor, label: "System" },
    { value: "light", Icon: Sun, label: "Light" },
    { value: "dark", Icon: Moon, label: "Dark" },
  ];
  // Native radios give arrow-key navigation for free; they are visually
  // hidden and the icon in the label is what the user sees.
  return (
    <fieldset className="inline-flex overflow-hidden rounded-md border border-border">
      <legend className="sr-only">Color mode</legend>
      {options.map(({ value, Icon, label }) => (
        <label
          key={value}
          className={cn(
            "flex h-6 w-6 cursor-pointer items-center justify-center text-muted-foreground hover:text-foreground",
            "focus-within:ring-2 focus-within:ring-ring focus-within:ring-inset",
            mode === value && "bg-accent text-foreground",
          )}
        >
          <input
            type="radio"
            name={groupName}
            value={value}
            checked={mode === value}
            onChange={() => pick(value)}
            className="sr-only"
          />
          <span className="sr-only">{label}</span>
          <Icon className="h-3.5 w-3.5" aria-hidden="true" />
        </label>
      ))}
    </fieldset>
  );
}
