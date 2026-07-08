import { useTranslation } from "react-i18next";
import { FileText, Plus, Search } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function Documents() {
  const { t } = useTranslation();

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Documents</h1>
          <p className="text-muted-foreground mt-1">Manage project deliverables and documentation</p>
        </div>
        <Button className="gap-2">
          <Plus className="w-4 h-4" />
          Upload Document
        </Button>
      </div>

      {/* Search and Filters */}
      <div className="flex gap-3">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-3 w-4 h-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search documents..."
            className="w-full pl-10 pr-4 py-2 rounded-lg border border-border bg-background text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary"
          />
        </div>
      </div>

      {/* Empty State */}
      <div className="rounded-lg border border-dashed border-border bg-card/30 p-12 text-center">
        <FileText className="w-12 h-12 text-muted-foreground/30 mx-auto mb-4" />
        <h3 className="text-lg font-semibold text-foreground mb-2">No documents yet</h3>
        <p className="text-muted-foreground mb-6">Upload project documents and deliverables</p>
        <Button>Upload First Document</Button>
      </div>
    </div>
  );
}
