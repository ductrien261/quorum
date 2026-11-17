"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import useSWR from "swr";

import { ChangePct, Empty, ErrorBox, PriceText, RankDelta, Skeleton, StarButton, TickerLink } from "@/components/ui/bits";
import { QuorumStrip } from "@/components/ui/quorum-strip";
import { type BoardRow, fetcher } from "@/lib/api";
import { money } from "@/lib/format";
import { usePageContext, useSession } from "@/lib/session";

export default function WatchlistPage() {
  usePageContext("Theo dõi");
  const router = useRouter();
  const { user, ready, watchlist } = useSession();
  const { data, error } = useSWR<{ symbols: string[]; rows: BoardRow[] }>(user ? ["/api/watchlist", watchlist.join(",")] : null, ([p]: [string, string]) =>
    fetcher<{ symbols: string[]; rows: BoardRow[] }>(p),
  );

  if (!ready) return <Skeleton className="mx-auto h-60 max-w-[1100px]" />;
  if (!user)
    return (
      <div className="panel mx-auto max-w-[560px]">
        <Empty title="Đăng nhập để lưu danh sách theo dõi">
          <p>Bấm ngôi sao cạnh một mã ở bất kỳ trang nào để theo dõi, rồi xem tất cả ở đây cùng hạng AI mới nhất.</p>
          <div className="mt-4 flex justify-center gap-2">
            <Link href="/dang-nhap?next=/theo-doi" className="btn-primary">
              Đăng nhập
            </Link>
            <Link href="/dang-ky?next=/theo-doi" className="btn">
              Tạo tài khoản
            </Link>
          </div>
        </Empty>
      </div>
    );
  if (error) return <ErrorBox error={error} />;

  return (
    <div className="mx-auto max-w-[1100px]">
      <div className="mb-3">
        <h1 className="text-lg font-bold">Danh sách theo dõi</h1>
        <p className="text-sm text-ink-2">Các mã bạn đã gắn sao, kèm giá phiên gần nhất và hạng AI cho phiên tới.</p>
      </div>
      <section className="panel">
        {!data ? (
          <Skeleton className="h-60" />
        ) : data.rows.length === 0 ? (
          <Empty title="Chưa theo dõi mã nào">
            Mở <Link href="/bang-gia" className="text-brand hover:underline">bảng giá</Link> hoặc{" "}
            <Link href="/goi-y" className="text-brand hover:underline">gợi ý AI</Link> và bấm ngôi sao cạnh mã bạn quan tâm.
          </Empty>
        ) : (
          <table className="tbl">
            <thead>
              <tr>
                <th className="w-8" />
                <th>Mã</th>
                <th>Ngành</th>
                <th className="text-right">Giá</th>
                <th className="text-right">%</th>
                <th className="text-right">Giá trị GD</th>
                <th className="text-right">Hạng AI</th>
                <th>Thay đổi hạng</th>
                <th>Đồng thuận</th>
              </tr>
            </thead>
            <tbody>
              {data.rows.map((r) => (
                <tr key={r.symbol} className="cursor-pointer" onClick={() => router.push(`/co-phieu/${r.symbol}`)}>
                  <td onClick={(e) => e.stopPropagation()}>
                    <StarButton symbol={r.symbol} />
                  </td>
                  <td>
                    <TickerLink symbol={r.symbol} />
                    <span className="ml-2 text-xs text-ink-3">{r.short_name}</span>
                  </td>
                  <td className="text-ink-2">{r.sector}</td>
                  <td className="text-right">
                    <PriceText value={r.close} refPrice={r.ref} ceil={r.ceiling} floor={r.floor} />
                  </td>
                  <td className="text-right">
                    <ChangePct value={r.change_pct} />
                  </td>
                  <td className="num text-right text-ink-2">{money(r.value)}</td>
                  <td className="num text-right font-semibold">{r.ai_rank ?? "–"}</td>
                  <td>
                    <RankDelta value={r.ai_rank_change} />
                  </td>
                  <td>{r.ai_votes != null && <QuorumStrip votes={r.ai_votes} size="sm" />}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}
