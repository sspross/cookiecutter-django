import { useState } from "react";
import { Button } from "@/components/ui/button";

interface CopyButtonProps {
  value: string;
  label?: string;
  "data-testid"?: string;
}

export function CopyButton({ value, label, "data-testid": testId }: CopyButtonProps) {
  const [copied, setCopied] = useState(false);
  async function copy() {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      setCopied(false);
    }
  }
  return (
    <Button
      type="button"
      variant="outline"
      size="sm"
      onClick={copy}
      data-testid={testId}
    >
      {copied ? "Copied!" : (label ?? "Copy")}
    </Button>
  );
}
