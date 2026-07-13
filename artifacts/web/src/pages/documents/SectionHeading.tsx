import type { ElementType } from "react";

// Consistent, understated section marker used to make the page read as one
// workflow (Upload -> Document Library -> Document Details -> OCR ->
// Contract Analysis) instead of a stack of same-weight cards. No icons-in-
// circles, no numbering — just a small uppercase eyebrow, matching the
// "nothing flashy, enterprise feel" brief.

export default function SectionHeading({
  icon: Icon,
  title,
  description,
}: {
  icon: ElementType;
  title: string;
  description?: string;
}) {
  return (
    <div className="flex items-center gap-2 mb-3">
      <Icon className="w-4 h-4 text-muted-foreground shrink-0" />
      <div>
        <h2 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">{title}</h2>
        {description && <p className="text-sm text-foreground mt-0.5">{description}</p>}
      </div>
    </div>
  );
}
