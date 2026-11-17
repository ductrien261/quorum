import clsx from "clsx";

/**
 * The quorum: one cell per model in the ensemble, filled when that model
 * puts the stock in its top 5. This is the product's signature element.
 */
export function QuorumStrip({
  votes,
  seeds = 10,
  size = "md",
  showLabel = true,
}: {
  votes: number;
  seeds?: number;
  size?: "sm" | "md" | "lg";
  showLabel?: boolean;
}) {
  const dims = { sm: "h-2.5 w-[5px]", md: "h-3.5 w-[7px]", lg: "h-5 w-[10px]" }[size];
  const strong = votes >= Math.ceil(seeds / 2);
  return (
    <span
      className="inline-flex items-center gap-2"
      title={`${votes}/${seeds} mô hình xếp mã này vào top 5`}
      aria-label={`${votes} trên ${seeds} mô hình đồng thuận`}
    >
      <span className="inline-flex gap-[2px]">
        {Array.from({ length: seeds }, (_, i) => (
          <span key={i} className={clsx(dims, i < votes ? (strong ? "bg-brand" : "bg-brand/60") : "bg-line")} />
        ))}
      </span>
      {showLabel && (
        <span className={clsx("num text-xs", strong ? "font-semibold text-brand" : "text-ink-2")}>
          {votes}/{seeds}
        </span>
      )}
    </span>
  );
}
