import { Link } from "wouter";
import { Home, AlertTriangle } from "lucide-react";

export default function NotFound() {
  return (
    <div className="min-h-screen w-full flex items-center justify-center bg-background p-6">
      <div className="panel max-w-md w-full">
        <div className="panel-body flex flex-col items-center text-center gap-6 py-10">
          <div className="w-16 h-16 rounded-2xl bg-destructive/10 flex items-center justify-center">
            <AlertTriangle className="w-8 h-8 text-destructive" />
          </div>

          <div>
            <p className="text-6xl font-bold text-foreground/20 tracking-tighter mb-3">404</p>
            <h1 className="text-xl font-bold text-foreground">Page Not Found</h1>
            <p className="mt-2 text-sm text-muted-foreground">
              The page you're looking for doesn't exist or you don't have permission to view it.
            </p>
          </div>

          <Link
            href="/"
            className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:opacity-90 transition-opacity"
          >
            <Home className="w-4 h-4" />
            Return to Dashboard
          </Link>
        </div>
      </div>
    </div>
  );
}
