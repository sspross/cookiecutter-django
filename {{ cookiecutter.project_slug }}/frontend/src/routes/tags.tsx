import { zodResolver } from "@hookform/resolvers/zod";
import { useNavigate, useSearch } from "@tanstack/react-router";
import { Pencil, Plus, Tag as TagIcon, Trash2 } from "lucide-react";
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
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { applyApiErrorsToForm } from "@/lib/rhf-errors";
import {
  type Tag,
  useCreateTag,
  useDeleteTag,
  useTagsList,
  useUpdateTag,
} from "@/resources/tags";

export const tagsSearchSchema = z.object({
  name: z.string().optional(),
  slug: z.string().optional(),
  limit: z.coerce.number().int().min(1).max(100).catch(20).default(20),
  offset: z.coerce.number().int().min(0).catch(0).default(0),
});

export type TagsSearch = z.infer<typeof tagsSearchSchema>;

const tagFormSchema = z.object({
  name: z.string().min(1, "Name is required").max(50),
  slug: z
    .string()
    .min(1, "Slug is required")
    .max(60)
    .regex(/^[-a-zA-Z0-9_]+$/u, "Slug may only contain letters, numbers, hyphens, underscores"),
});
type TagFormValues = z.infer<typeof tagFormSchema>;

export function TagsPage() {
  const search = useSearch({ from: "/tags" });
  const navigate = useNavigate({ from: "/tags" });

  const list = useTagsList({
    name: search.name,
    slug: search.slug,
    limit: search.limit,
    offset: search.offset,
  });

  const [createOpen, setCreateOpen] = useState(false);
  const [editing, setEditing] = useState<Tag | null>(null);
  const [deleting, setDeleting] = useState<Tag | null>(null);

  const updateSearch = (next: Partial<TagsSearch>) =>
    navigate({
      search: (prev) => ({ ...prev, ...next }),
    });

  const items = list.data?.items ?? [];
  const total = list.data?.count ?? 0;

  return (
    <main
      className="mx-auto flex min-h-screen max-w-4xl flex-col gap-6 px-6 py-12"
      data-testid="tags-page"
    >
      <header className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <TagIcon className="h-6 w-6 text-primary" />
          <h1 className="text-2xl font-semibold tracking-tight">Tags</h1>
        </div>
        <Button
          size="sm"
          onClick={() => setCreateOpen(true)}
          data-testid="tags-create-button"
        >
          <Plus className="h-4 w-4" />
          New tag
        </Button>
      </header>

      <section className="flex flex-wrap items-end gap-3">
        <div className="flex flex-col gap-1">
          <Label htmlFor="filter-name">Name contains</Label>
          <Input
            id="filter-name"
            data-testid="tags-filter-name"
            value={search.name ?? ""}
            onChange={(e) =>
              updateSearch({
                name: e.target.value || undefined,
                offset: 0,
              })
            }
            placeholder="filter by name"
          />
        </div>
        <div className="flex flex-col gap-1">
          <Label htmlFor="filter-slug">Slug contains</Label>
          <Input
            id="filter-slug"
            data-testid="tags-filter-slug"
            value={search.slug ?? ""}
            onChange={(e) =>
              updateSearch({
                slug: e.target.value || undefined,
                offset: 0,
              })
            }
            placeholder="filter by slug"
          />
        </div>
      </section>

      <section
        className="rounded-lg border border-border"
        data-testid="tags-list"
      >
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Slug</TableHead>
              <TableHead className="w-[140px] text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {list.isLoading ? (
              <TableRow>
                <TableCell colSpan={3} className="text-muted-foreground">
                  Loading…
                </TableCell>
              </TableRow>
            ) : items.length === 0 ? (
              <TableRow>
                <TableCell colSpan={3} className="text-muted-foreground">
                  No tags match the current filter.
                </TableCell>
              </TableRow>
            ) : (
              items.map((tag) => (
                <TableRow key={tag.id}>
                  <TableCell className="font-medium">{tag.name}</TableCell>
                  <TableCell className="font-mono text-xs">{tag.slug}</TableCell>
                  <TableCell className="text-right">
                    <Button
                      variant="ghost"
                      size="sm"
                      data-testid={`tag-edit-${tag.slug}`}
                      onClick={() => setEditing(tag)}
                    >
                      <Pencil className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      data-testid={`tag-delete-${tag.slug}`}
                      onClick={() => setDeleting(tag)}
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

      <CreateTagDialog
        open={createOpen}
        onOpenChange={setCreateOpen}
      />

      {editing ? (
        <EditTagDialog
          tag={editing}
          onClose={() => setEditing(null)}
        />
      ) : null}

      {deleting ? (
        <DeleteTagDialog
          tag={deleting}
          onClose={() => setDeleting(null)}
        />
      ) : null}
    </main>
  );
}

function CreateTagDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (next: boolean) => void;
}) {
  const create = useCreateTag();
  const form = useForm<TagFormValues>({
    resolver: zodResolver(tagFormSchema),
    defaultValues: { name: "", slug: "" },
  });

  useEffect(() => {
    if (!open) form.reset({ name: "", slug: "" });
  }, [open, form]);

  const onSubmit = form.handleSubmit(async (values) => {
    try {
      await create.mutateAsync(values);
      onOpenChange(false);
    } catch (err) {
      if (!applyApiErrorsToForm(form, err)) {
        form.setError("root.serverError", {
          type: "server",
          message: "Could not save tag.",
        });
      }
    }
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>New tag</DialogTitle>
          <DialogDescription>
            Tags can be attached to other resources to group them.
          </DialogDescription>
        </DialogHeader>
        <TagFormFields form={form} onSubmit={onSubmit} />
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
            data-testid="tag-form-submit"
          >
            Create
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function EditTagDialog({ tag, onClose }: { tag: Tag; onClose: () => void }) {
  const update = useUpdateTag(tag.id);
  const form = useForm<TagFormValues>({
    resolver: zodResolver(tagFormSchema),
    defaultValues: { name: tag.name, slug: tag.slug },
  });

  const onSubmit = form.handleSubmit(async (values) => {
    try {
      await update.mutateAsync(values);
      onClose();
    } catch (err) {
      if (!applyApiErrorsToForm(form, err)) {
        form.setError("root.serverError", {
          type: "server",
          message: "Could not save tag.",
        });
      }
    }
  });

  return (
    <Dialog open onOpenChange={(next) => !next && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Edit tag</DialogTitle>
          <DialogDescription>Update the tag's name or slug.</DialogDescription>
        </DialogHeader>
        <TagFormFields form={form} onSubmit={onSubmit} />
        <DialogFooter>
          <Button variant="outline" type="button" onClick={onClose}>
            Cancel
          </Button>
          <Button
            type="button"
            onClick={onSubmit}
            disabled={update.isPending}
            data-testid="tag-form-submit"
          >
            Save
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function DeleteTagDialog({ tag, onClose }: { tag: Tag; onClose: () => void }) {
  const del = useDeleteTag();
  const onConfirm = async () => {
    try {
      await del.mutateAsync(tag.id);
    } finally {
      onClose();
    }
  };
  return (
    <Dialog open onOpenChange={(next) => !next && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Delete tag</DialogTitle>
          <DialogDescription>
            Permanently remove "{tag.name}"? This cannot be undone.
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
            data-testid="tag-delete-confirm"
          >
            Delete
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function TagFormFields({
  form,
  onSubmit,
}: {
  form: ReturnType<typeof useForm<TagFormValues>>;
  onSubmit: (e?: React.BaseSyntheticEvent) => Promise<void>;
}) {
  const rootError = form.formState.errors.root?.serverError?.message;
  return (
    <form onSubmit={onSubmit} className="flex flex-col gap-3">
      <div className="flex flex-col gap-1">
        <Label htmlFor="tag-name">Name</Label>
        <Input
          id="tag-name"
          data-testid="tag-form-name"
          {...form.register("name")}
        />
        {form.formState.errors.name ? (
          <p className="text-sm text-destructive">
            {form.formState.errors.name.message}
          </p>
        ) : null}
      </div>
      <div className="flex flex-col gap-1">
        <Label htmlFor="tag-slug">Slug</Label>
        <Input
          id="tag-slug"
          data-testid="tag-form-slug"
          {...form.register("slug")}
        />
        {form.formState.errors.slug ? (
          <p className="text-sm text-destructive">
            {form.formState.errors.slug.message}
          </p>
        ) : null}
      </div>
      {rootError ? (
        <p className="text-sm text-destructive">{rootError}</p>
      ) : null}
    </form>
  );
}
