import Link from "next/link";

export default function NotFound() {
  return (
    <div className="panel mx-auto max-w-[520px] px-6 py-10 text-center">
      <p className="text-lg font-bold">Không tìm thấy trang này</p>
      <p className="mt-1 text-sm text-ink-2">Có thể mã chứng khoán không nằm trong rổ 78 mã Quorum theo dõi, hoặc đường dẫn đã thay đổi.</p>
      <Link href="/" className="btn-primary mt-4">
        Về trang tổng quan
      </Link>
    </div>
  );
}
