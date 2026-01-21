interface VisuallyHiddenProps {
  children: React.ReactNode;
  /** Set to true to make visible when focused */
  focusable?: boolean;
}

/**
 * VisuallyHidden component - Content hidden visually but available to screen readers
 * Use for additional context, labels, or instructions
 */
export function VisuallyHidden({ children, focusable = false }: VisuallyHiddenProps) {
  if (focusable) {
    return <span className="sr-only sr-only-focusable">{children}</span>;
  }
  return <span className="sr-only">{children}</span>;
}
