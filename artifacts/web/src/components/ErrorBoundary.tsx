import { Component, type ErrorInfo, type ReactNode } from "react";
import { AlertTriangle, RotateCcw } from "lucide-react";

// Class component — React error boundaries cannot be implemented with hooks,
// so this can't use useTranslation(); it reads documentElement.lang directly
// instead, which is set by the language toggle in components/layout.tsx and
// survives independently of whatever crashed.
function isArabic(): boolean {
  if (typeof document === "undefined") return false;
  return document.documentElement.lang === "ar" || document.documentElement.dir === "rtl";
}

interface Props {
  children: ReactNode;
  /** Rendered full-height, centered — for a whole route/page. Otherwise renders
   * as an inline card sized to its container (for wrapping one panel among siblings). */
  fullPage?: boolean;
  /** Renders nothing on error instead of a card — for elements that don't
   * occupy normal document flow (e.g. a fixed-position floating button),
   * where an inline fallback card would otherwise inject unwanted layout. */
  silent?: boolean;
}

interface State {
  hasError: boolean;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(): State {
    return { hasError: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    // eslint-disable-next-line no-console
    console.error("ErrorBoundary caught a render error:", error, info.componentStack);
  }

  private reset = () => {
    this.setState({ hasError: false });
  };

  render() {
    if (!this.state.hasError) return this.props.children;
    if (this.props.silent) return null;

    const ar = isArabic();
    const wrapperClass = this.props.fullPage
      ? "min-h-[50vh] flex items-center justify-center p-6"
      : "flex items-center justify-center p-6 h-full min-h-[200px]";

    return (
      <div className={wrapperClass} dir={ar ? "rtl" : "ltr"}>
        <div className="max-w-sm w-full rounded-xl border border-destructive/30 bg-destructive/5 p-6 text-center space-y-3">
          <div className="mx-auto w-10 h-10 rounded-full bg-destructive/10 flex items-center justify-center">
            <AlertTriangle className="w-5 h-5 text-destructive" />
          </div>
          <div className="space-y-1">
            <p className="text-sm font-semibold text-foreground">
              {ar ? "حدث خطأ غير متوقع" : "Something went wrong"}
            </p>
            <p className="text-xs text-muted-foreground">
              {ar
                ? "حدث خطأ أثناء عرض هذا الجزء. باقي التطبيق ما زال يعمل."
                : "This part of the page failed to load. The rest of the app is still working."}
            </p>
          </div>
          <button
            onClick={this.reset}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-destructive/10 text-destructive hover:bg-destructive/15 transition-colors"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            {ar ? "إعادة المحاولة" : "Try again"}
          </button>
        </div>
      </div>
    );
  }
}
