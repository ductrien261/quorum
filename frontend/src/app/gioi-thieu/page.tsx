import Link from "next/link";

import { LogoMark } from "@/components/ui/logo";
import { QuorumStrip } from "@/components/ui/quorum-strip";

export const metadata = { title: "Cách Quorum hoạt động" };

const STEPS = [
  {
    title: "Thu thập sau phiên",
    body: "16:30 mỗi ngày giao dịch, Quorum lấy giá đóng cửa của 78 mã (nguồn KBS), VN-Index và tin tức mới trên CafeF.",
  },
  {
    title: "Dựng bức tranh 16 phiên",
    body: "Mỗi mã có 7 chỉ báo kỹ thuật (lợi suất 1, 5, 10 phiên, RSI, MACD, tương quan giá đóng/mở, biên độ). 16 phiên gần nhất của cả 78 mã xếp thành một khối dữ liệu, các mã cùng ngành đứng cạnh nhau.",
  },
  {
    title: "10 mô hình cùng chấm điểm",
    body: "Mô hình học sâu MIDMoE đọc khối dữ liệu đó, tin tức và quan hệ ngành rồi chấm điểm từng mã. 10 bản mô hình huấn luyện độc lập cùng chấm; thứ hạng cuối là trung bình của cả 10.",
  },
  {
    title: "Giải thích và trả lời",
    body: "Với mỗi mã, Quorum thử bỏ từng nguồn thông tin để biết nguồn nào đang đẩy hạng lên. Trợ lý AI dùng chính những số liệu đó để trả lời câu hỏi của bạn.",
  },
];

export default function AboutPage() {
  return (
    <div className="mx-auto grid max-w-[880px] gap-6 py-2">
      <header className="flex items-start gap-4">
        <LogoMark size={44} className="mt-1 shrink-0 text-brand" />
        <div>
          <h1 className="text-xl font-bold">Cách Quorum hoạt động</h1>
          <p className="mt-2 max-w-[66ch] text-base text-ink-2">
            Quorum là số phiếu tối thiểu để một hội đồng ra quyết định. Ở đây, hội đồng là 10 mô hình AI: một mã chỉ thật sự nổi bật khi
            nhiều mô hình cùng xếp nó lên đầu.
          </p>
        </div>
      </header>

      <section className="panel p-5">
        <h2 className="text-md font-semibold">Đọc dải đồng thuận</h2>
        <div className="mt-3 grid gap-3 sm:grid-cols-3">
          {[
            [8, "8 trên 10 mô hình xếp mã vào top 5: các mô hình nhất trí cao."],
            [4, "4 trên 10: có tín hiệu nhưng các mô hình còn chia rẽ."],
            [1, "1 trên 10: mã lọt top nhờ trung bình thứ hạng, ít mô hình thật sự chọn."],
          ].map(([v, t]) => (
            <div key={v as number} className="border border-line-soft p-3">
              <QuorumStrip votes={v as number} size="lg" />
              <p className="mt-2 text-sm text-ink-2">{t}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="panel">
        <h2 className="border-b border-line px-5 py-3 text-md font-semibold">Mỗi tối diễn ra 4 bước</h2>
        <ol>
          {STEPS.map((s, i) => (
            <li key={s.title} className="grid grid-cols-[40px_1fr] gap-3 border-b border-line-soft px-5 py-4 last:border-b-0">
              <span className="num text-lg font-bold text-brand">{i + 1}</span>
              <div>
                <h3 className="font-semibold">{s.title}</h3>
                <p className="mt-1 max-w-[70ch] text-sm text-ink-2">{s.body}</p>
              </div>
            </li>
          ))}
        </ol>
      </section>

      <section className="panel p-5">
        <h2 className="text-md font-semibold">Nên dùng điểm AI thế nào</h2>
        <ul className="mt-2 grid list-[square] gap-1.5 pl-5 text-sm text-ink-2">
          <li>Xem như một góc nhìn để thu hẹp danh sách, không phải lệnh mua bán.</li>
          <li>
            Trên dữ liệu kiểm định năm 2025, top 5 chỉ nhỉnh hơn chọn ngẫu nhiên và chưa có ý nghĩa thống kê. Số liệu đầy đủ ở trang{" "}
            <Link href="/hieu-qua" className="text-brand hover:underline">
              hiệu quả gợi ý
            </Link>
            .
          </li>
          <li>Mô hình chưa tính phí giao dịch, thuế, quy tắc T+2 và biên độ trần/sàn.</li>
          <li>Chỉ 78 mã thanh khoản tốt (VN30 và một số mã vốn hoá vừa) có điểm AI.</li>
        </ul>
      </section>

    </div>
  );
}
