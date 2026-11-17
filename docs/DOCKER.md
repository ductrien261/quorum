# Chạy Quorum bằng Docker trên Windows

Hai container: `api` (FastAPI + mô hình + lịch chạy 16:30) ở cổng 8000 và `web` (Next.js) ở cổng 3000.
Cơ sở dữ liệu SQLite và model PhoBERT nằm trong Docker volume, nên tắt và bật lại container không mất dữ liệu.

## 1. Chuẩn bị (một lần)

1. Cài **Docker Desktop**: https://www.docker.com/products/docker-desktop/. Lúc cài, giữ tuỳ chọn *Use WSL 2*.
   Khởi động lại máy nếu được yêu cầu.
2. Mở Docker Desktop, đợi góc dưới bên trái báo *Engine running*.
3. Kiểm tra trong PowerShell:

   ```powershell
   docker --version
   docker compose version
   ```

4. Trong thư mục `quorum` phải có:
   * file `.env` đã điền `GEMINI_API_KEY` (bạn đã làm);
   * thư mục `artifacts\vn\` chứa `weights\model_seed0.pt` … `model_seed9.pt` (đã chép sẵn).

Docker Desktop cần khoảng 8 GB ổ đĩa cho image và dữ liệu. Nếu máy có dưới 8 GB RAM, vào *Settings → Resources* đặt
Memory tối thiểu 4 GB, vì PhoBERT cần khoảng 2 GB khi nhúng tin.

## 2. Chạy lần đầu: một lệnh

Mở PowerShell tại thư mục `quorum`:

```powershell
cd "D:\VKU-Studying\03. Academic_Resources\Semester_7_2026-2027\Đồ án CN 2\quorum"
powershell -ExecutionPolicy Bypass -File scripts\first-run.ps1
```

Script làm lần lượt:

| Bước | Việc | Thời gian ước tính |
| --- | --- | --- |
| 1 | Build 2 image và khởi động container | 5-15 phút (lần đầu tải PyTorch CPU, thư viện Node) |
| 2 | Chạy test: mô hình phải ra đúng điểm số như notebook Kaggle | dưới 1 phút |
| 3 | Nạp 243 phiên kiểm định 2025 | 1-2 phút |
| 4 | Tải giá 78 mã + VN-Index từ KBS | khoảng 2 phút |
| 5 | Tải tin CafeF 14 ngày gần nhất, nhúng bằng PhoBERT | 20-60 phút (lần đầu tải thêm model ~540 MB) |
| 6 | Chạy mô hình cho từng phiên từ 02/01/2026 đến hôm nay | khoảng 5 phút |

Xong, mở http://localhost:3000.

Muốn thấy giao diện nhanh trước rồi mới tải tin: `-NewsDays 0` để bỏ qua bước 5, tải tin sau bằng lệnh ở mục 4.

```powershell
powershell -ExecutionPolicy Bypass -File scripts\first-run.ps1 -NewsDays 0
```

## 3. Dùng hằng ngày

```powershell
docker compose up -d          # bật (nếu đã tắt)
docker compose ps             # xem trạng thái, api phải là "healthy"
docker compose logs -f api    # xem log backend (Ctrl+C để thoát xem log, container vẫn chạy)
docker compose down           # tắt, dữ liệu vẫn giữ
```

Không cần chạy lệnh gì để lấy dữ liệu. Khi container `api` đang chạy:

- **Mỗi lần khởi động** (bật máy, `docker compose up -d`): job bù dữ liệu chạy ngầm, kéo giá và tin còn thiếu, chạy
  mô hình cho mọi phiên đã đóng cửa mà chưa có dự báo, rồi tính lợi suất thực tế. Tắt máy cả tuần thì lúc bật lại nó tự
  bù cả tuần. Tin tức chỉ bù tối đa 14 ngày gần nhất.
- **9:00–14:55, thứ 2 đến thứ 6:** cập nhật giá 5 phút một lần cho bảng giá.
- **16:30, thứ 2 đến thứ 6:** job chính (giá, tin, dự báo cho phiên hôm nay).

Xem job đã chạy chưa: `docker compose logs api | findstr catch-up`. Muốn chạy tay:

```powershell
docker compose exec api python -m app.cli catch-up   # bù mọi thứ còn thiếu
docker compose exec api python -m app.cli daily      # chỉ phiên mới nhất
```

## 4. Các lệnh dữ liệu

Mọi lệnh `python -m app.cli …` trong README đều chạy được bằng cách thêm `docker compose exec api` phía trước:

```powershell
docker compose exec api python -m app.cli prices                       # cập nhật giá
docker compose exec api python -m app.cli news --from 2026-11-01       # tải thêm tin
docker compose exec api python -m app.cli backfill --from 2026-11-01   # chạy lại mô hình cho một khoảng ngày
docker compose exec api python -m pytest                               # chạy toàn bộ test
```

## 5. Sửa code rồi cập nhật container

```powershell
docker compose up -d --build api    # sau khi sửa backend
docker compose up -d --build web    # sau khi sửa frontend
```

Khi đang phát triển giao diện, chạy frontend ngoài Docker cho nhanh (tự tải lại khi lưu file), backend vẫn để trong Docker:

```powershell
docker compose stop web
cd frontend
npm install
npm run dev
```

## 6. Làm lại từ đầu

```powershell
docker compose down -v      # -v xoá cả cơ sở dữ liệu và model PhoBERT đã tải
powershell -ExecutionPolicy Bypass -File scripts\first-run.ps1 -SkipBuild
```

## Lỗi thường gặp

| Hiện tượng | Cách xử lý |
| --- | --- |
| `docker: command not found` hoặc `Docker chua chay` | Mở Docker Desktop, đợi *Engine running* |
| `port is already allocated` (8000 hoặc 3000) | Một chương trình khác đang dùng cổng: tắt nó, hoặc đổi `"8000:8000"` thành `"8010:8000"` trong `docker-compose.yml` (đổi cổng API thì sửa luôn `NEXT_PUBLIC_API_URL` ở mục `web` rồi build lại `web`) |
| Web báo "Không kết nối được máy chủ Quorum" | `docker compose ps` xem `api` có chạy không; `docker compose logs api` xem lỗi |
| Bước tải giá báo lỗi KBS | Mạng chặn hoặc KBS tạm lỗi: chạy lại `docker compose exec api python -m app.cli prices` |
| Trợ lý báo lỗi 404 model | Tên model Gemini đã đổi: sửa `GEMINI_MODEL` trong `.env`, rồi `docker compose up -d api` |
| Trợ lý báo hết hạn mức (429) | Gói miễn phí của Gemini giới hạn số lần gọi mỗi ngày: đợi, hoặc bật thanh toán cho key |
| Script `.ps1` bị chặn | Chạy đúng dạng `powershell -ExecutionPolicy Bypass -File scripts\first-run.ps1` |
