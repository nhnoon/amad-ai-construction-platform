import { useEffect, useState } from "react";
import { useListProjects } from "@workspace/api-client-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription,
} from "@/components/ui/dialog";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Loader2 } from "lucide-react";
import {
  createMemoryRecord, updateMemoryRecord, AICenterApiError,
  USER_MEMORY_CATEGORIES, type UserMemoryCategory, type StructuredMemory,
} from "@/lib/aiCenterClient";

// Add/Edit Memory — the Memory Center's professional replacement for the
// old "Remember that..." chat command (Product UX Phase 1 §2). Same
// dialog handles both: editingRecord present -> PATCH, absent -> POST.

export function MemoryFormDialog({
  open, onOpenChange, editingRecord, defaultProjectCode, onSaved,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  editingRecord: StructuredMemory | null;
  defaultProjectCode?: string | null;
  onSaved: () => void;
}) {
  const { data: projects } = useListProjects({ limit: 100 });
  const [title, setTitle] = useState("");
  const [summary, setSummary] = useState("");
  const [category, setCategory] = useState<UserMemoryCategory>("personal_note");
  const [projectCode, setProjectCode] = useState<string>("none");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isEdit = !!editingRecord;

  useEffect(() => {
    if (!open) return;
    if (editingRecord) {
      setTitle(editingRecord.title);
      setSummary(editingRecord.summary);
      const known = USER_MEMORY_CATEGORIES.find((c) => c.value === editingRecord.category);
      setCategory(known ? known.value : "personal_note");
      setProjectCode(editingRecord.project_code ?? "none");
    } else {
      setTitle("");
      setSummary("");
      setCategory("personal_note");
      setProjectCode(defaultProjectCode ?? "none");
    }
    setError(null);
  }, [open, editingRecord, defaultProjectCode]);

  const canSubmit = title.trim().length > 0 && summary.trim().length > 0 && !submitting;

  const handleSubmit = async () => {
    if (!canSubmit) return;
    setSubmitting(true);
    setError(null);
    try {
      if (isEdit && editingRecord) {
        await updateMemoryRecord(editingRecord.id, {
          title: title.trim(),
          summary: summary.trim(),
          category,
        });
      } else {
        await createMemoryRecord({
          title: title.trim(),
          summary: summary.trim(),
          category,
          projectCode: projectCode === "none" ? null : projectCode,
        });
      }
      onSaved();
      onOpenChange(false);
    } catch (err) {
      setError(err instanceof AICenterApiError ? err.message : "Failed to save memory.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>{isEdit ? "Edit Memory" : "Add Memory"}</DialogTitle>
          <DialogDescription>
            {isEdit
              ? "Update this memory. It stays visible to your team and to Hermes as historical context."
              : "Save a note your team — and Hermes — can recall later. Not a chat command: this is stored directly."}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          <div className="space-y-1.5">
            <label className="text-sm font-medium">Title</label>
            <Input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Crane rental renewal due"
              maxLength={255}
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <label className="text-sm font-medium">Category</label>
              <Select value={category} onValueChange={(v) => setCategory(v as UserMemoryCategory)}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {USER_MEMORY_CATEGORIES.map((c) => (
                    <SelectItem key={c.value} value={c.value}>{c.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <label className="text-sm font-medium">Project (optional)</label>
              <Select value={projectCode} onValueChange={setProjectCode} disabled={isEdit}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">No project</SelectItem>
                  {projects?.map((p) => (
                    <SelectItem key={p.id} value={p.project_code}>{p.project_code}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="space-y-1.5">
            <label className="text-sm font-medium">Summary</label>
            <Textarea
              value={summary}
              onChange={(e) => setSummary(e.target.value)}
              placeholder="What should be remembered? Be specific — this is what Hermes will read back later."
              rows={4}
              maxLength={1000}
            />
            <p className="text-xs text-muted-foreground text-right">{summary.length}/1000</p>
          </div>

          {error && <p className="text-sm text-destructive">{error}</p>}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={submitting}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={!canSubmit}>
            {submitting ? (
              <><Loader2 className="mr-2 h-4 w-4 animate-spin" />{isEdit ? "Saving..." : "Adding..."}</>
            ) : (
              isEdit ? "Save Changes" : "Add Memory"
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
