import { zodResolver } from "@hookform/resolvers/zod";
import {
  Link,
  useNavigate,
  useParams,
  useSearch,
} from "@tanstack/react-router";
import { ArrowLeft, FolderKanban, Pencil, Plus, Trash2 } from "lucide-react";
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
import { useProject } from "@/resources/projects";
import {
  type Task,
  type TaskPriority,
  type TaskStatus,
  useCreateTask,
  useDeleteTask,
  useTasksList,
  useUpdateTask,
} from "@/resources/tasks";

const STATUSES: TaskStatus[] = ["todo", "in_progress", "done", "blocked"];
const PRIORITIES: TaskPriority[] = ["low", "medium", "high", "urgent"];

export const projectDetailSearchSchema = z.object({
  status: z.enum(["todo", "in_progress", "done", "blocked"]).optional(),
  priority: z.enum(["low", "medium", "high", "urgent"]).optional(),
  due_from: z.string().optional(),
  due_to: z.string().optional(),
  limit: z.coerce.number().int().min(1).max(100).catch(20).default(20),
  offset: z.coerce.number().int().min(0).catch(0).default(0),
});
export type ProjectDetailSearch = z.infer<typeof projectDetailSearchSchema>;

const taskFormSchema = z.object({
  title: z.string().min(1, "Title is required").max(200),
  description: z.string().max(2000).optional().default(""),
  status: z.enum(["todo", "in_progress", "done", "blocked"]),
  priority: z.enum(["low", "medium", "high", "urgent"]),
  due_date: z
    .string()
    .regex(/^\d{4}-\d{2}-\d{2}$/u, "Use YYYY-MM-DD")
    .optional()
    .or(z.literal("")),
});
type TaskFormValues = z.infer<typeof taskFormSchema>;

export function ProjectDetailPage() {
  const { projectId } = useParams({ from: "/projects/$projectId" });
  const search = useSearch({ from: "/projects/$projectId" });
  const navigate = useNavigate({ from: "/projects/$projectId" });
  const id = Number(projectId);
  const project = useProject(id);

  const tasks = useTasksList({
    project: id,
    status: search.status,
    priority: search.priority,
    due_from: search.due_from,
    due_to: search.due_to,
    limit: search.limit,
    offset: search.offset,
  });

  const [createOpen, setCreateOpen] = useState(false);
  const [editing, setEditing] = useState<Task | null>(null);
  const [deleting, setDeleting] = useState<Task | null>(null);

  const updateSearch = (next: Partial<ProjectDetailSearch>) =>
    navigate({ search: (prev) => ({ ...prev, ...next }) });

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
  const taskItems = tasks.data?.items ?? [];
  const total = tasks.data?.count ?? 0;

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

      <section className="flex flex-col gap-3">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-medium">Tasks</h2>
          <Button
            size="sm"
            onClick={() => setCreateOpen(true)}
            data-testid="tasks-create-button"
          >
            <Plus className="h-4 w-4" />
            New task
          </Button>
        </div>
        <div className="flex flex-wrap items-end gap-3">
          <div className="flex flex-col gap-1">
            <Label htmlFor="task-filter-status">Status</Label>
            <Select
              id="task-filter-status"
              data-testid="tasks-filter-status"
              value={search.status ?? ""}
              onChange={(e) =>
                updateSearch({
                  status: (e.target.value || undefined) as
                    | TaskStatus
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
            <Label htmlFor="task-filter-priority">Priority</Label>
            <Select
              id="task-filter-priority"
              data-testid="tasks-filter-priority"
              value={search.priority ?? ""}
              onChange={(e) =>
                updateSearch({
                  priority: (e.target.value || undefined) as
                    | TaskPriority
                    | undefined,
                  offset: 0,
                })
              }
            >
              <option value="">all</option>
              {PRIORITIES.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </Select>
          </div>
          <div className="flex flex-col gap-1">
            <Label htmlFor="task-filter-due-from">Due from</Label>
            <Input
              id="task-filter-due-from"
              type="date"
              data-testid="tasks-filter-due-from"
              value={search.due_from ?? ""}
              onChange={(e) =>
                updateSearch({
                  due_from: e.target.value || undefined,
                  offset: 0,
                })
              }
            />
          </div>
          <div className="flex flex-col gap-1">
            <Label htmlFor="task-filter-due-to">Due to</Label>
            <Input
              id="task-filter-due-to"
              type="date"
              data-testid="tasks-filter-due-to"
              value={search.due_to ?? ""}
              onChange={(e) =>
                updateSearch({
                  due_to: e.target.value || undefined,
                  offset: 0,
                })
              }
            />
          </div>
        </div>
        <div
          className="rounded-lg border border-border"
          data-testid="tasks-list"
        >
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Title</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Priority</TableHead>
                <TableHead>Due</TableHead>
                <TableHead className="w-[140px] text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {tasks.isLoading ? (
                <TableRow>
                  <TableCell colSpan={5} className="text-muted-foreground">
                    Loading…
                  </TableCell>
                </TableRow>
              ) : taskItems.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={5} className="text-muted-foreground">
                    No tasks match the current filter.
                  </TableCell>
                </TableRow>
              ) : (
                taskItems.map((task) => (
                  <TableRow key={task.id}>
                    <TableCell className="font-medium">{task.title}</TableCell>
                    <TableCell>
                      <span className="rounded bg-secondary px-2 py-0.5 text-xs font-medium">
                        {task.status}
                      </span>
                    </TableCell>
                    <TableCell className="text-xs">{task.priority}</TableCell>
                    <TableCell className="text-xs">
                      {task.due_date ?? "—"}
                    </TableCell>
                    <TableCell className="text-right">
                      <Button
                        variant="ghost"
                        size="sm"
                        data-testid={`task-edit-${task.id}`}
                        onClick={() => setEditing(task)}
                      >
                        <Pencil className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        data-testid={`task-delete-${task.id}`}
                        onClick={() => setDeleting(task)}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>
        <footer className="flex items-center justify-between text-sm text-muted-foreground">
          <span>
            Showing {taskItems.length === 0 ? 0 : search.offset + 1}–
            {Math.min(search.offset + taskItems.length, total)} of {total}
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
      </section>

      <CreateTaskDialog
        projectId={p.id}
        open={createOpen}
        onOpenChange={setCreateOpen}
      />
      {editing ? (
        <EditTaskDialog
          task={editing}
          onClose={() => setEditing(null)}
        />
      ) : null}
      {deleting ? (
        <DeleteTaskDialog
          task={deleting}
          onClose={() => setDeleting(null)}
        />
      ) : null}
    </main>
  );
}

function CreateTaskDialog({
  projectId,
  open,
  onOpenChange,
}: {
  projectId: number;
  open: boolean;
  onOpenChange: (next: boolean) => void;
}) {
  const create = useCreateTask();
  const form = useForm<TaskFormValues>({
    resolver: zodResolver(taskFormSchema),
    defaultValues: {
      title: "",
      description: "",
      status: "todo",
      priority: "medium",
      due_date: "",
    },
  });

  useEffect(() => {
    if (!open) {
      form.reset({
        title: "",
        description: "",
        status: "todo",
        priority: "medium",
        due_date: "",
      });
    }
  }, [open, form]);

  const onSubmit = form.handleSubmit(async (values) => {
    try {
      await create.mutateAsync({
        project_id: projectId,
        title: values.title,
        description: values.description,
        status: values.status,
        priority: values.priority,
        due_date: values.due_date ? values.due_date : null,
      });
      onOpenChange(false);
    } catch (err) {
      if (!applyApiErrorsToForm(form, err)) {
        form.setError("root.serverError", {
          type: "server",
          message: "Could not save task.",
        });
      }
    }
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>New task</DialogTitle>
          <DialogDescription>
            Add work to this project. Due date and priority help with
            filtering.
          </DialogDescription>
        </DialogHeader>
        <TaskFormFields form={form} onSubmit={onSubmit} />
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
            data-testid="task-form-submit"
          >
            Create
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function EditTaskDialog({ task, onClose }: { task: Task; onClose: () => void }) {
  const update = useUpdateTask(task.id);
  const form = useForm<TaskFormValues>({
    resolver: zodResolver(taskFormSchema),
    defaultValues: {
      title: task.title,
      description: task.description,
      status: task.status,
      priority: task.priority,
      due_date: task.due_date ?? "",
    },
  });

  const onSubmit = form.handleSubmit(async (values) => {
    try {
      await update.mutateAsync({
        title: values.title,
        description: values.description,
        status: values.status,
        priority: values.priority,
        due_date: values.due_date ? values.due_date : null,
      });
      onClose();
    } catch (err) {
      if (!applyApiErrorsToForm(form, err)) {
        form.setError("root.serverError", {
          type: "server",
          message: "Could not save task.",
        });
      }
    }
  });

  return (
    <Dialog open onOpenChange={(next) => !next && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Edit task</DialogTitle>
          <DialogDescription>
            Change the title, status, priority, or due date.
          </DialogDescription>
        </DialogHeader>
        <TaskFormFields form={form} onSubmit={onSubmit} />
        <DialogFooter>
          <Button variant="outline" type="button" onClick={onClose}>
            Cancel
          </Button>
          <Button
            type="button"
            onClick={onSubmit}
            disabled={update.isPending}
            data-testid="task-form-submit"
          >
            Save
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function DeleteTaskDialog({
  task,
  onClose,
}: {
  task: Task;
  onClose: () => void;
}) {
  const del = useDeleteTask();
  const onConfirm = async () => {
    try {
      await del.mutateAsync({ id: task.id, projectId: task.project_id });
    } finally {
      onClose();
    }
  };
  return (
    <Dialog open onOpenChange={(next) => !next && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Delete task</DialogTitle>
          <DialogDescription>
            Permanently remove "{task.title}"? This cannot be undone.
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
            data-testid="task-delete-confirm"
          >
            Delete
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function TaskFormFields({
  form,
  onSubmit,
}: {
  form: ReturnType<typeof useForm<TaskFormValues>>;
  onSubmit: (e?: React.BaseSyntheticEvent) => Promise<void>;
}) {
  const rootError = form.formState.errors.root?.serverError?.message;
  return (
    <form onSubmit={onSubmit} className="flex flex-col gap-3">
      <div className="flex flex-col gap-1">
        <Label htmlFor="task-title">Title</Label>
        <Input
          id="task-title"
          data-testid="task-form-title"
          {...form.register("title")}
        />
        {form.formState.errors.title ? (
          <p className="text-sm text-destructive">
            {form.formState.errors.title.message}
          </p>
        ) : null}
      </div>
      <div className="flex flex-col gap-1">
        <Label htmlFor="task-description">Description</Label>
        <Textarea
          id="task-description"
          data-testid="task-form-description"
          {...form.register("description")}
        />
      </div>
      <div className="flex gap-3">
        <div className="flex flex-1 flex-col gap-1">
          <Label htmlFor="task-status">Status</Label>
          <Select
            id="task-status"
            data-testid="task-form-status"
            {...form.register("status")}
          >
            {STATUSES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </Select>
        </div>
        <div className="flex flex-1 flex-col gap-1">
          <Label htmlFor="task-priority">Priority</Label>
          <Select
            id="task-priority"
            data-testid="task-form-priority"
            {...form.register("priority")}
          >
            {PRIORITIES.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </Select>
        </div>
      </div>
      <div className="flex flex-col gap-1">
        <Label htmlFor="task-due-date">Due date</Label>
        <Input
          id="task-due-date"
          type="date"
          data-testid="task-form-due-date"
          {...form.register("due_date")}
        />
        {form.formState.errors.due_date ? (
          <p className="text-sm text-destructive">
            {form.formState.errors.due_date.message}
          </p>
        ) : null}
      </div>
      {rootError ? (
        <p className="text-sm text-destructive">{rootError}</p>
      ) : null}
    </form>
  );
}
