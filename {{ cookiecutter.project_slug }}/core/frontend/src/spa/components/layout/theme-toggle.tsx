import { useId } from "react";
import { Monitor, Moon, Sun } from "@/components/layout/icons";
import { type ColorMode, useColorMode } from "@/hooks/use-color-mode";
import { cn } from "@/lib/utils";

export function ThemeToggle() {
  const [mode, pick] = useColorMode();
  const radioGroupNameUniquePerInstance = useId();

  const options: { value: ColorMode; Icon: typeof Sun; label: string }[] = [
    { value: "system", Icon: Monitor, label: "System" },
    { value: "light", Icon: Sun, label: "Light" },
    { value: "dark", Icon: Moon, label: "Dark" },
  ];
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
            name={radioGroupNameUniquePerInstance}
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
