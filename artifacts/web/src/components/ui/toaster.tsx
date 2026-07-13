import { CheckCircle2, AlertTriangle, AlertOctagon, Info } from "lucide-react"
import { useToast } from "@/hooks/use-toast"
import {
  Toast,
  ToastClose,
  ToastDescription,
  ToastProvider,
  ToastTitle,
  ToastViewport,
} from "@/components/ui/toast"

// One icon per variant, matching the semantic colors already used for
// badges/status chips elsewhere (`.badge-success/.badge-warning/...`) so a
// toast reads the same way as any other status indicator in the app.
const VARIANT_ICON = {
  success: CheckCircle2,
  warning: AlertTriangle,
  destructive: AlertOctagon,
  info: Info,
} as const

export function Toaster() {
  const { toasts } = useToast()

  return (
    <ToastProvider>
      {toasts.map(function ({ id, title, description, action, variant, ...props }) {
        const Icon = variant ? VARIANT_ICON[variant as keyof typeof VARIANT_ICON] : undefined
        return (
          <Toast key={id} variant={variant} {...props}>
            <div className="flex items-start gap-3">
              {Icon && <Icon className="h-5 w-5 shrink-0 mt-0.5" />}
              <div className="grid gap-1">
                {title && <ToastTitle>{title}</ToastTitle>}
                {description && (
                  <ToastDescription>{description}</ToastDescription>
                )}
              </div>
            </div>
            {action}
            <ToastClose />
          </Toast>
        )
      })}
      <ToastViewport />
    </ToastProvider>
  )
}
