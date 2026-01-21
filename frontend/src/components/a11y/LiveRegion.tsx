"use client";

import { useEffect, useRef } from "react";

interface LiveRegionProps {
  message: string;
  role: "status" | "alert";
  className?: string;
}

/**
 * LiveRegion component - Announces dynamic content to screen readers
 * WCAG 2.1 Success Criterion 4.1.3: Status Messages
 */
export function LiveRegion({ message, role, className = "" }: LiveRegionProps) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (ref.current && message) {
      // Clear and reset to ensure announcement
      ref.current.textContent = "";
      setTimeout(() => {
        if (ref.current) {
          ref.current.textContent = message;
        }
      }, 100);
    }
  }, [message]);

  return (
    <div
      ref={ref}
      role={role}
      aria-live="polite"
      aria-atomic="true"
      className="sr-only"
    >
      {message}
    </div>
  );
}
