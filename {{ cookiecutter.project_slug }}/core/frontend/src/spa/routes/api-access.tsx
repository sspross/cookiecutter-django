import { useState } from "react";
import type { ApiKey, ApiKeyMintOut } from "@/api/client";
import {
  MintApiKeyModal,
  RevealApiKeyModal,
  RevokeApiKeyModal,
} from "@/components/api-key-modals";
import { CopyButton } from "@/components/copy-button";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useApiKeysList } from "@/queries/use-api-keys";

function formatTimestamp(iso: string | null | undefined) {
  if (!iso) return "Never";
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

// `window` is always defined here — the SPA only runs in the browser.
const ORIGIN = window.location.origin;
const PREFIX_HINT = "{{ cookiecutter.project_slug }}_live_…";

const CURL_LIST = `curl -H "Authorization: Bearer ${PREFIX_HINT}" \\
  ${ORIGIN}/api/api-keys/`;

type Modal =
  | { kind: "none" }
  | { kind: "mint" }
  | { kind: "reveal"; result: ApiKeyMintOut }
  | { kind: "revoke"; key: ApiKey };

export function ApiAccessRoute() {
  const list = useApiKeysList();
  const [modal, setModal] = useState<Modal>({ kind: "none" });

  const keys = list.data ?? [];
  const isEmpty = list.isSuccess && keys.length === 0;

  return (
    <div className="space-y-10" data-testid="api-access">
      <section className="space-y-4">
        <div className="flex items-end justify-between">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">API Access</h1>
            <p className="text-sm text-muted-foreground">
              Manage personal API keys for headless access.
            </p>
          </div>
          {!isEmpty && (
            <Button data-testid="open-mint" onClick={() => setModal({ kind: "mint" })}>
              New API key
            </Button>
          )}
        </div>

        <h2 className="text-lg font-semibold tracking-tight">Your keys</h2>

        {list.isLoading && (
          <div className="space-y-2" data-testid="api-keys-loading">
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
          </div>
        )}

        {list.isError && (
          <p className="text-sm text-destructive">
            Failed to load API keys: {String(list.error)}
          </p>
        )}

        {isEmpty && (
          <div
            className="rounded-md border border-dashed p-12 text-center"
            data-testid="api-keys-empty"
          >
            <p className="text-sm text-muted-foreground">
              You haven't minted any API keys yet.
            </p>
            <Button
              className="mt-4"
              data-testid="empty-state-mint"
              onClick={() => setModal({ kind: "mint" })}
            >
              Create your first API key
            </Button>
          </div>
        )}

        {!isEmpty && keys.length > 0 && (
          <div className="overflow-hidden rounded-md border">
            <Table data-testid="api-keys-table">
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Prefix</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead>Last used</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {keys.map((key) => {
                  const revoked = key.revoked_at !== null;
                  return (
                    <TableRow key={key.id} data-testid={`api-key-row-${key.id}`}>
                      <TableCell className="font-medium">{key.name}</TableCell>
                      <TableCell className="font-mono text-xs">{key.prefix}…</TableCell>
                      <TableCell className="font-mono text-xs text-muted-foreground">
                        {formatTimestamp(key.created_at)}
                      </TableCell>
                      <TableCell className="font-mono text-xs text-muted-foreground">
                        {formatTimestamp(key.last_used_at)}
                      </TableCell>
                      <TableCell>
                        {revoked ? (
                          <Badge
                            variant="muted"
                            data-testid={`api-key-revoked-${key.id}`}
                          >
                            Revoked
                          </Badge>
                        ) : (
                          <Badge variant="success">Active</Badge>
                        )}
                      </TableCell>
                      <TableCell className="text-right">
                        {!revoked && (
                          <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            data-testid={`revoke-${key.id}`}
                            onClick={() => setModal({ kind: "revoke", key })}
                          >
                            Revoke
                          </Button>
                        )}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </div>
        )}
      </section>

      <section className="space-y-4">
        <h2 className="text-lg font-semibold tracking-tight">Quickstart</h2>
        <p className="text-sm text-muted-foreground">
          Replace <code className="font-mono">{PREFIX_HINT}</code> with the token you
          minted above. Bearer auth is accepted on every endpoint except{" "}
          <code className="font-mono">/api/api-keys/*</code> (session-only).
        </p>

        <div className="space-y-2">
          <div className="flex items-start gap-2">
            <pre className="flex-1 overflow-x-auto rounded-md border bg-muted px-3 py-2 font-mono text-xs">
              {CURL_LIST}
            </pre>
            <CopyButton value={CURL_LIST} />
          </div>
        </div>
      </section>

      <section className="space-y-2">
        <h2 className="text-lg font-semibold tracking-tight">API reference</h2>
        <p className="text-sm text-muted-foreground">
          Browse every endpoint and schema in the auto-generated Swagger UI.
        </p>
        <a
          href="/api/docs"
          target="_blank"
          rel="noopener noreferrer"
          className="text-sm text-primary underline-offset-4 hover:underline"
          data-testid="swagger-link"
        >
          Open API reference →
        </a>
      </section>

      <MintApiKeyModal
        open={modal.kind === "mint"}
        onOpenChange={(open) => !open && setModal({ kind: "none" })}
        onMinted={(result) => setModal({ kind: "reveal", result })}
      />
      <RevealApiKeyModal
        result={modal.kind === "reveal" ? modal.result : null}
        onAcknowledge={() => setModal({ kind: "none" })}
      />
      <RevokeApiKeyModal
        apiKey={modal.kind === "revoke" ? modal.key : null}
        onClose={() => setModal({ kind: "none" })}
      />
    </div>
  );
}
