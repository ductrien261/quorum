/**
 * Quorum mark: a square frame whose tail breaks out of the corner (the Q),
 * holding three rising bars (a ranking). Drawn on a 32px grid with square caps.
 */
export function LogoMark({ size = 24, className }: { size?: number; className?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none" aria-hidden className={className}>
      <path d="M4 4H26V26H4Z" stroke="currentColor" strokeWidth="3" strokeLinejoin="miter" />
      <path d="M21 21L29.5 29.5" stroke="currentColor" strokeWidth="3" strokeLinecap="square" />
      <rect x="8.5" y="15" width="3" height="6" fill="currentColor" />
      <rect x="13.5" y="12" width="3" height="9" fill="currentColor" />
      <rect x="18.5" y="9" width="3" height="7" fill="currentColor" />
    </svg>
  );
}

export function Logo({ compact = false }: { compact?: boolean }) {
  return (
    <span className="inline-flex items-center gap-2 text-brand">
      <LogoMark size={22} />
      {!compact && <span className="text-[17px] font-bold tracking-[-0.01em] text-ink">Quorum</span>}
    </span>
  );
}
