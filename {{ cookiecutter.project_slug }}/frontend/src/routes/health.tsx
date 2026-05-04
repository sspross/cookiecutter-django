import { useQuery } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Activity, RefreshCw } from "lucide-react";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";

const noteSchema = z.object({
  note: z.string().min(1, "Note cannot be empty").max(80, "Too long"),
});

type NoteFormValues = z.infer<typeof noteSchema>;

export function HealthPage() {
  const healthQuery = useQuery({
    queryKey: ["health"],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/health");
      if (error) throw error;
      return data;
    },
  });

  const configQuery = useQuery({
    queryKey: ["config"],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/config");
      if (error) throw error;
      return data;
    },
  });

  const form = useForm<NoteFormValues>({
    resolver: zodResolver(noteSchema),
    defaultValues: { note: "" },
  });

  return (
    <main
      className="mx-auto flex min-h-screen max-w-2xl flex-col gap-6 px-6 py-12"
      data-testid="health-page"
    >
      <header className="flex items-center gap-3">
        <Activity className="h-6 w-6 text-primary" />
        <h1 className="text-2xl font-semibold tracking-tight">
          {configQuery.data?.project_name ?? "App"}
        </h1>
      </header>

      <section className="rounded-lg border border-border p-6">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-medium">Health</h2>
          <Button
            variant="outline"
            size="sm"
            onClick={() => healthQuery.refetch()}
            disabled={healthQuery.isFetching}
          >
            <RefreshCw className="h-4 w-4" />
            Refresh
          </Button>
        </div>
        <p className="mt-2 text-sm text-muted-foreground">
          Status:{" "}
          <span data-testid="health-status" className="font-mono">
            {healthQuery.data?.status ?? (healthQuery.isLoading ? "…" : "?")}
          </span>
        </p>
      </section>

      <section className="rounded-lg border border-border p-6">
        <h2 className="text-lg font-medium">Form (RHF + Zod)</h2>
        <form
          className="mt-3 flex flex-col gap-2"
          onSubmit={form.handleSubmit((values) => {
            window.alert(`Note: ${values.note}`);
          })}
        >
          <input
            type="text"
            placeholder="Type a note"
            className="rounded-md border border-input bg-background px-3 py-2 text-sm"
            {...form.register("note")}
          />
          {form.formState.errors.note ? (
            <p className="text-sm text-destructive">
              {form.formState.errors.note.message}
            </p>
          ) : null}
          <Button type="submit" size="sm">
            Submit
          </Button>
        </form>
      </section>
    </main>
  );
}
