import { Button } from "@/components/ui/button";
import { useTimedFlag } from "@/hooks/use-timed-flag";

const COPIED_LABEL_MS = 1500;

interface CopyButtonProps {
  value: string;
  label?: string;
  "data-testid"?: string;
}

export function CopyButton({ value, label, "data-testid": testId }: CopyButtonProps) {
  const [copied, showCopied] = useTimedFlag(COPIED_LABEL_MS);
  async function copy() {
    try {
      await navigator.clipboard.writeText(value);
    } catch {
      return;
    }
    showCopied();
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
