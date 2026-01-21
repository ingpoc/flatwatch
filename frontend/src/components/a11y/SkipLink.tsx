/**
 * SkipLink component - Allows keyboard users to skip navigation
 * WCAG 2.1 Success Criterion 2.4.1: Bypass Blocks
 */
export function SkipLink() {
  return (
    <a
      href="#main-content"
      className="skip-link"
    >
      Skip to main content
    </a>
  );
}
