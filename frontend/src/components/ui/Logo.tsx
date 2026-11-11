/**
 * Placeholder Monroe Fund mark: a blue sailboat inside an engraved ring, with a
 * brass waterline. Swap for the final artwork when it exists. Sails and hull use
 * currentColor (the accent), so it follows light/dark mode.
 * Decorative; callers provide the accessible name.
 */
export function Logo({ size = 36, className }: { size?: number; className?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 40 40" className={className} aria-hidden="true" focusable="false">
      <circle cx="20" cy="20" r="19" fill="none" stroke="currentColor" strokeWidth="1" />
      <circle cx="20" cy="20" r="16.5" fill="none" stroke="currentColor" strokeWidth="0.5" strokeDasharray="1 1.6" opacity="0.6" />
      {/* Mainsail and jib */}
      <path d="M20.5 8.5 L20.5 25 L29 25 Z" fill="currentColor" />
      <path d="M19 12 L19 25 L12.5 25 Z" fill="currentColor" opacity="0.6" />
      {/* Hull */}
      <path d="M11 26.5 H30 L27.2 30 H13.6 Z" fill="currentColor" />
      {/* Waterline */}
      <path
        d="M9.5 32.5 q2.6 -1.6 5.2 0 t5.2 0 t5.2 0 t5.2 0"
        fill="none"
        strokeWidth="1.1"
        strokeLinecap="round"
        style={{ stroke: "var(--color-brass)" }}
      />
    </svg>
  );
}
