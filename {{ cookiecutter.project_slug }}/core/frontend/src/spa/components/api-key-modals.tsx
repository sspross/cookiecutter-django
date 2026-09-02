import { useState } from "react";
import type { ApiKey, ApiKeyMintOut } from "@/api/client";
import { CopyButton } from "@/components/copy-button";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useMintApiKey, useRevokeApiKey } from "@/queries/use-api-keys";

interface MintModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onMinted: (result: ApiKeyMintOut) => void;
}

export function MintApiKeyModal({ open, onOpenChange, onMinted }: MintModalProps) {
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const mint = useMintApiKey();

  function reset() {
    setName("");
    setError(null);
  }

  function submit() {
    if (!name.trim()) {
      setError("Name is required.");
      return;
    }
    setError(null);
    mint.mutate(
      { name: name.trim() },
      {
        onSuccess: (result) => {
          reset();
          onOpenChange(false);
          onMinted(result);
        },
        onError: (err) => {
          setError(err.message ?? "Failed to mint key.");
        },
      },
    );
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!next) reset();
        onOpenChange(next);
      }}
    >
      <DialogContent>
        <DialogHeader>
          <DialogTitle>New API key</DialogTitle>
          <DialogDescription>
            Give your key a short label so you can tell it apart later.
          </DialogDescription>
        </DialogHeader>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            submit();
          }}
          className="space-y-4"
        >
          <div className="space-y-2">
            <Label htmlFor="api-key-name">Name</Label>
            <Input
              id="api-key-name"
              data-testid="api-key-name"
              value={name}
              autoFocus
              onChange={(e) => setName(e.target.value)}
            />
            {error && <p className="text-xs text-destructive">{error}</p>}
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button
              type="button"
              data-testid="submit-mint"
              disabled={mint.isPending}
              onClick={submit}
            >
              {mint.isPending ? "Creating…" : "Create key"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

interface RevealModalProps {
  result: ApiKeyMintOut | null;
  onAcknowledge: () => void;
}

export function RevealApiKeyModal({ result, onAcknowledge }: RevealModalProps) {
  // Acknowledgement-required: Esc and outside-clicks are suppressed so the
  // only exit is the explicit "I've copied it" button.
  return (
    <Dialog open={result !== null}>
      <DialogContent
        data-testid="reveal-modal"
        onEscapeKeyDown={(e) => e.preventDefault()}
        onPointerDownOutside={(e) => e.preventDefault()}
        onInteractOutside={(e) => e.preventDefault()}
        // Hide the built-in close icon; the ack button is the only exit.
        className="[&>button[aria-label=Close]]:hidden"
      >
        <DialogHeader>
          <DialogTitle>Copy your API key now</DialogTitle>
          <DialogDescription>
            This is the <strong>only</strong> time the full token will be shown. Store
            it somewhere safe — once you close this dialog, it is gone.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-3">
          <pre
            data-testid="raw-token"
            className="overflow-x-auto rounded-md border bg-muted px-3 py-2 font-mono text-xs"
          >
            {result?.raw_token ?? ""}
          </pre>
          <CopyButton
            value={result?.raw_token ?? ""}
            label="Copy to clipboard"
            data-testid="copy-token"
          />
        </div>
        <DialogFooter>
          <Button type="button" data-testid="ack-token" onClick={onAcknowledge}>
            I've copied it
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

interface RevokeModalProps {
  apiKey: ApiKey | null;
  onClose: () => void;
}

export function RevokeApiKeyModal({ apiKey, onClose }: RevokeModalProps) {
  const revoke = useRevokeApiKey();

  function confirm() {
    if (!apiKey) return;
    revoke.mutate(apiKey.id, {
      onSuccess: () => onClose(),
      onError: () => onClose(),
    });
  }

  return (
    <Dialog
      open={apiKey !== null}
      onOpenChange={(next) => {
        if (!next) onClose();
      }}
    >
      <DialogContent data-testid="revoke-modal">
        <DialogHeader>
          <DialogTitle>Revoke API key?</DialogTitle>
          <DialogDescription>
            <code className="font-mono">{apiKey?.name}</code> (prefix{" "}
            <code className="font-mono">{apiKey?.prefix}</code>) will stop
            authenticating immediately. This cannot be undone — the key will remain
            visible in your list with a "Revoked" badge for audit purposes.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button type="button" variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button
            type="button"
            variant="destructive"
            data-testid="confirm-revoke"
            disabled={revoke.isPending}
            onClick={confirm}
          >
            {revoke.isPending ? "Revoking…" : "Revoke key"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
