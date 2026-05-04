import { Link, useParams } from "@tanstack/react-router";
import { ArrowLeft, FolderKanban } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useProject } from "@/resources/projects";

export function ProjectDetailPage() {
  const { projectId } = useParams({ from: "/projects/$projectId" });
  const id = Number(projectId);
  const project = useProject(id);

  if (project.isLoading) {
    return (
      <main className="mx-auto flex min-h-screen max-w-4xl flex-col gap-6 px-6 py-12">
        <p className="text-sm text-muted-foreground">Loading…</p>
      </main>
    );
  }

  if (project.isError || !project.data) {
    return (
      <main className="mx-auto flex min-h-screen max-w-4xl flex-col gap-6 px-6 py-12">
        <Link
          to="/projects"
          className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:underline"
        >
          <ArrowLeft className="h-4 w-4" /> Back to projects
        </Link>
        <p className="text-sm text-destructive">Project not found.</p>
      </main>
    );
  }

  const p = project.data;

  return (
    <main
      className="mx-auto flex min-h-screen max-w-4xl flex-col gap-6 px-6 py-12"
      data-testid="project-detail-page"
    >
      <div>
        <Button variant="ghost" size="sm" asChild>
          <Link to="/projects">
            <ArrowLeft className="h-4 w-4" /> Back to projects
          </Link>
        </Button>
      </div>
      <header className="flex items-center gap-3">
        <FolderKanban className="h-6 w-6 text-primary" />
        <h1
          className="text-2xl font-semibold tracking-tight"
          data-testid="project-detail-title"
        >
          {p.title}
        </h1>
        <span className="rounded bg-secondary px-2 py-0.5 text-xs font-medium">
          {p.status}
        </span>
      </header>
      <section className="rounded-lg border border-border p-6">
        <h2 className="text-sm font-medium text-muted-foreground">
          Description
        </h2>
        <p className="mt-1 whitespace-pre-wrap text-sm">
          {p.description || "—"}
        </p>
      </section>
      <section className="rounded-lg border border-border p-6">
        <h2 className="text-sm font-medium text-muted-foreground">Tags</h2>
        <div className="mt-2 flex flex-wrap gap-2">
          {p.tags.length === 0 ? (
            <span className="text-sm text-muted-foreground">No tags.</span>
          ) : (
            p.tags.map((t) => (
              <span
                key={t.id}
                className="rounded bg-secondary px-2 py-0.5 text-xs"
              >
                {t.name}
              </span>
            ))
          )}
        </div>
      </section>
    </main>
  );
}
