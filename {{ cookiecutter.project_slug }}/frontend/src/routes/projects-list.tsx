import { zodResolver } from "@hookform/resolvers/zod";
import { Link, useNavigate, useSearch } from "@tanstack/react-router";
import { FolderKanban, Pencil, Plus, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

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
import { Select } from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";
import { applyApiErrorsToForm } from "@/lib/rhf-errors";
import {
  type Project,
  type ProjectStatus,
  useCreateProject,
  useDeleteProject,
  useProjectsList,
  useUpdateProject,
} from "@/resources/projects";
import { useTagsList } from "@/resources/tags";

const STATUSES: ProjectStatus[] = ["draft", "active", "archived"];

export const projectsSearchSchema = z.object({
  title: z.string().optional(),
  status: z.enum(["draft", "active", "archived"]).optional(),
  tag: z.coerce.number().int().positive().optional(),
  limit: z.coerce.number().int().min(1).max(100).catch(20).default(20),
  offset: z.coerce.number().int().min(0).catch(0).default(0),
});
export type ProjectsSearch = z.infer<typeof projectsSearchSchema>;

const projectFormSchema = z.object({
  title: z.string().min(1, "Title is required").max(120),
  description: z.string().max(2000).optional().default(""),
  status: z.enum(["draft", "active", "archived"]),
  tagIds: z.array(z.number().int()).default([]),
});
type ProjectFormValues = z.infer<typeof projectFormSchema>;

export function ProjectsListPage() {
  const search = useSearch({ from: "/projects" });
  const navigate = useNavigate({ from: "/projects" });

  const list = useProjectsList({
    title: search.title,
    status: search.status,
    tag: search.tag,
    limit: search.limit,
    offset: search.offset,
  });

  const tagsForFilter = useTagsList({ limit: 100, offset: 0 });

  const [createOpen, setCreateOpen] = useState(false);
  const [editing, setEditing] = useState<Project | null>(null);
  const [deleting, setDeleting] = useState<Project | null>(null);

  const updateSearch = (next: Partial<ProjectsSearch>) =>
    navigate({ search: (prev) => ({ ...prev, ...next }) });

  const items = list.data?.items ?? [];
  const total = list.data?.count ?? 0;

  return (
    <main
      className="mx-auto flex min-h-screen max-w-5xl flex-col gap-6 px-6 py-12"
      data-testid="projects-page"
    >
      <header className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <FolderKanban className="h-6 w-6 text-primary" />
          <h1 className="text-2xl font-semibold tracking-tight">Projects</h1>
        </div>
        <Button
          size="sm"
          onClick={() => setCreateOpen(true)}
          data-testid="projects-create-button"
        >
          <Plus className="h-4 w-4" />
          New project
        </Button>
      </header>

      <section className="flex flex-wrap items-end gap-3">
        <div className="flex flex-col gap-1">
          <Label htmlFor="filter-title">Title contains</Label>
          <Input
            id="filter-title"
            data-testid="projects-filter-title"
            value={search.title ?? ""}
            onChange={(e) =>
              updateSearch({ title: e.target.value || undefined, offset: 0 })
            }
          />
        </div>
        <div className="flex flex-col gap-1">
          <Label htmlFor="filter-status">Status</Label>
          <Select
            id="filter-status"
            data-testid="projects-filter-status"
            value={search.status ?? ""}
            onChange={(e) =>
              updateSearch({
                status: (e.target.value || undefined) as
                  | ProjectStatus
                  | undefined,
                offset: 0,
              })
            }
          >
            <option value="">all</option>
            {STATUSES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </Select>
        </div>
        <div className="flex flex-col gap-1">
          <Label htmlFor="filter-tag">Tag</Label>
          <Select
            id="filter-tag"
            data-testid="projects-filter-tag"
            value={search.tag ?? ""}
            onChange={(e) =>
              updateSearch({
                tag: e.target.value ? Number(e.target.value) : undefined,
                offset: 0,
              })
            }
          >
            <option value="">all</option>
            {(tagsForFilter.data?.items ?? []).map((t) => (
              <option key={t.id} value={t.id}>
                {t.name}
              </option>
            ))}
          </Select>
        </div>
      </section>

      <section
        className="rounded-lg border border-border"
        data-testid="projects-list"
      >
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Title</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Tags</TableHead>
              <TableHead className="w-[160px] text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {list.isLoading ? (
              <TableRow>
                <TableCell colSpan={4} className="text-muted-foreground">
                  Loading…
                </TableCell>
              </TableRow>
            ) : items.length === 0 ? (
              <TableRow>
                <TableCell colSpan={4} className="text-muted-foreground">
                  No projects match the current filter.
                </TableCell>
              </TableRow>
            ) : (
              items.map((project) => (
                <TableRow key={project.id}>
                  <TableCell className="font-medium">
                    <Link
                      to="/projects/$projectId"
                      params={{ projectId: String(project.id) }}
                      className="underline-offset-2 hover:underline"
                      data-testid={`project-link-${project.id}`}
                    >
                      {project.title}
                    </Link>
                  </TableCell>
                  <TableCell>
                    <span
                      className="rounded bg-secondary px-2 py-0.5 text-xs font-medium"
                      data-testid={`project-status-${project.id}`}
                    >
                      {project.status}
                    </span>
                  </TableCell>
                  <TableCell className="text-xs">
                    {project.tags.map((t) => t.name).join(", ") || "—"}
                  </TableCell>
                  <TableCell className="text-right">
                    <Button
                      variant="ghost"
                      size="sm"
                      data-testid={`project-edit-${project.id}`}
                      onClick={() => setEditing(project)}
                    >
                      <Pencil className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      data-testid={`project-delete-${project.id}`}
                      onClick={() => setDeleting(project)}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </section>

      <footer className="flex items-center justify-between text-sm text-muted-foreground">
        <span>
          Showing {items.length === 0 ? 0 : search.offset + 1}–
          {Math.min(search.offset + items.length, total)} of {total}
        </span>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            disabled={search.offset === 0}
            onClick={() =>
              updateSearch({
                offset: Math.max(0, search.offset - search.limit),
              })
            }
          >
            Previous
          </Button>
          <Button
            variant="outline"
            size="sm"
            disabled={search.offset + search.limit >= total}
            onClick={() =>
              updateSearch({ offset: search.offset + search.limit })
            }
          >
            Next
          </Button>
        </div>
      </footer>

      <CreateProjectDialog
        open={createOpen}
        onOpenChange={setCreateOpen}
      />
      {editing ? (
        <EditProjectDialog
          project={editing}
          onClose={() => setEditing(null)}
        />
      ) : null}
      {deleting ? (
        <DeleteProjectDialog
          project={deleting}
          onClose={() => setDeleting(null)}
        />
      ) : null}
    </main>
  );
}

function CreateProjectDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (next: boolean) => void;
}) {
  const tags = useTagsList({ limit: 100, offset: 0 });
  const create = useCreateProject();
  const form = useForm<ProjectFormValues>({
    resolver: zodResolver(projectFormSchema),
    defaultValues: { title: "", description: "", status: "draft", tagIds: [] },
  });

  useEffect(() => {
    if (!open) {
      form.reset({ title: "", description: "", status: "draft", tagIds: [] });
    }
  }, [open, form]);

  const onSubmit = form.handleSubmit(async (values) => {
    try {
      await create.mutateAsync({
        title: values.title,
        description: values.description,
        status: values.status,
        tag_ids: values.tagIds,
      });
      onOpenChange(false);
    } catch (err) {
      if (!applyApiErrorsToForm(form, err)) {
        form.setError("root.serverError", {
          type: "server",
          message: "Could not save project.",
        });
      }
    }
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>New project</DialogTitle>
          <DialogDescription>
            Group related work and tag it for later filtering.
          </DialogDescription>
        </DialogHeader>
        <ProjectFormFields
          form={form}
          tagOptions={tags.data?.items ?? []}
          onSubmit={onSubmit}
        />
        <DialogFooter>
          <Button
            variant="outline"
            type="button"
            onClick={() => onOpenChange(false)}
          >
            Cancel
          </Button>
          <Button
            type="button"
            onClick={onSubmit}
            disabled={create.isPending}
            data-testid="project-form-submit"
          >
            Create
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function EditProjectDialog({
  project,
  onClose,
}: {
  project: Project;
  onClose: () => void;
}) {
  const tags = useTagsList({ limit: 100, offset: 0 });
  const update = useUpdateProject(project.id);
  const form = useForm<ProjectFormValues>({
    resolver: zodResolver(projectFormSchema),
    defaultValues: {
      title: project.title,
      description: project.description,
      status: project.status,
      tagIds: project.tags.map((t) => t.id),
    },
  });

  const onSubmit = form.handleSubmit(async (values) => {
    try {
      await update.mutateAsync({
        title: values.title,
        description: values.description,
        status: values.status,
        tag_ids: values.tagIds,
      });
      onClose();
    } catch (err) {
      if (!applyApiErrorsToForm(form, err)) {
        form.setError("root.serverError", {
          type: "server",
          message: "Could not save project.",
        });
      }
    }
  });

  return (
    <Dialog open onOpenChange={(next) => !next && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Edit project</DialogTitle>
          <DialogDescription>
            Change the title, status, or attached tags.
          </DialogDescription>
        </DialogHeader>
        <ProjectFormFields
          form={form}
          tagOptions={tags.data?.items ?? []}
          onSubmit={onSubmit}
        />
        <DialogFooter>
          <Button variant="outline" type="button" onClick={onClose}>
            Cancel
          </Button>
          <Button
            type="button"
            onClick={onSubmit}
            disabled={update.isPending}
            data-testid="project-form-submit"
          >
            Save
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function DeleteProjectDialog({
  project,
  onClose,
}: {
  project: Project;
  onClose: () => void;
}) {
  const del = useDeleteProject();
  const onConfirm = async () => {
    try {
      await del.mutateAsync(project.id);
    } finally {
      onClose();
    }
  };
  return (
    <Dialog open onOpenChange={(next) => !next && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Delete project</DialogTitle>
          <DialogDescription>
            Permanently remove "{project.title}"? This cannot be undone.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button variant="outline" type="button" onClick={onClose}>
            Cancel
          </Button>
          <Button
            variant="destructive"
            type="button"
            onClick={onConfirm}
            disabled={del.isPending}
            data-testid="project-delete-confirm"
          >
            Delete
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function ProjectFormFields({
  form,
  tagOptions,
  onSubmit,
}: {
  form: ReturnType<typeof useForm<ProjectFormValues>>;
  tagOptions: { id: number; name: string }[];
  onSubmit: (e?: React.BaseSyntheticEvent) => Promise<void>;
}) {
  const rootError = form.formState.errors.root?.serverError?.message;
  const selectedTagIds = form.watch("tagIds");

  return (
    <form onSubmit={onSubmit} className="flex flex-col gap-3">
      <div className="flex flex-col gap-1">
        <Label htmlFor="project-title">Title</Label>
        <Input
          id="project-title"
          data-testid="project-form-title"
          {...form.register("title")}
        />
        {form.formState.errors.title ? (
          <p className="text-sm text-destructive">
            {form.formState.errors.title.message}
          </p>
        ) : null}
      </div>
      <div className="flex flex-col gap-1">
        <Label htmlFor="project-description">Description</Label>
        <Textarea
          id="project-description"
          data-testid="project-form-description"
          {...form.register("description")}
        />
      </div>
      <div className="flex flex-col gap-1">
        <Label htmlFor="project-status">Status</Label>
        <Select
          id="project-status"
          data-testid="project-form-status"
          {...form.register("status")}
        >
          {STATUSES.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </Select>
      </div>
      <fieldset className="flex flex-col gap-1">
        <legend className="text-sm font-medium leading-none">Tags</legend>
        <div
          className="mt-1 flex flex-wrap gap-3 rounded-md border border-input p-3"
          data-testid="project-form-tag-picker"
        >
          {tagOptions.length === 0 ? (
            <p className="text-sm text-muted-foreground">No tags available.</p>
          ) : (
            tagOptions.map((t) => {
              const checked = selectedTagIds.includes(t.id);
              return (
                <label
                  key={t.id}
                  className="flex items-center gap-1 text-sm"
                  data-testid={`project-form-tag-${t.id}`}
                >
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={(e) => {
                      const next = e.target.checked
                        ? [...selectedTagIds, t.id]
                        : selectedTagIds.filter((id) => id !== t.id);
                      form.setValue("tagIds", next, { shouldDirty: true });
                    }}
                  />
                  {t.name}
                </label>
              );
            })
          )}
        </div>
      </fieldset>
      {rootError ? (
        <p className="text-sm text-destructive">{rootError}</p>
      ) : null}
    </form>
  );
}
