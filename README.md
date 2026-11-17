# Quorum

Ứng dụng web gợi ý cổ phiếu Việt Nam. Mỗi tối sau phiên, mô hình học sâu **MIDMoE** chấm điểm 78 mã; 10 bản mô hình
cùng "bỏ phiếu", và mã được nhiều mô hình xếp vào top 5 sẽ nổi lên. Người dùng xem bảng giá, gợi ý cho phiên tới, lý do
xếp hạng, lọc cổ phiếu, theo dõi mã và hỏi trợ lý AI (Gemini) bằng tiếng Việt.

> Đồ án chuyên ngành 2, ngành Trí tuệ nhân tạo, VKU. Điểm AI là công cụ tham khảo, không phải khuyến nghị đầu tư.

## Thành phần

| Thư mục | Nội dung |
| --- | --- |
| `backend/app/ml/` | Kiến trúc MarketMoE (chép nguyên từ notebook Kaggle), 7 chỉ báo, dựng cube, PhoBERT, ensemble 10 seed, giải thích |
| `backend/app/sources/` | Giá ngày từ KBS (nguồn notebook đã dùng qua vnstock), tin tức từ trang tìm kiếm CafeF |
| `backend/app/pipeline/` | Job 16:30 hằng ngày, chạy bù (backfill), nạp lịch sử kiểm định 2025, dữ liệu giả lập |
| `backend/app/services/`, `api.py` | REST API: bảng giá, tổng quan, gợi ý, chi tiết mã, bộ lọc, hiệu quả, tài khoản, theo dõi |
| `backend/app/assistant/`, `chat.py` | Trợ lý Gemini gọi công cụ tra cứu dữ liệu (function calling), trả lời dạng stream |
| `frontend/` | Next.js 15 + TypeScript + Tailwind: 9 trang, sidebar trợ lý, biểu đồ lightweight-charts |
| `artifacts/vn/` | Trọng số và tham số chuẩn hoá xuất từ Kaggle (không commit, xem `artifacts/README.md`) |

```
KBS (giá) ─┐                                   ┌─► Next.js (localhost:3000)
CafeF (tin)┼─► pipeline 16:30 ─► SQLite/Postgres ◄─ FastAPI (localhost:8000) ◄─┤
artifacts ─┘   (10 seed + giải thích)                      │                    └─► Gemini API
                                                           └── trợ lý: công cụ đọc cùng service layer
```

## Chạy nhanh bằng Docker

Cần Docker Desktop, file `.env` đã điền `GEMINI_API_KEY` và thư mục `artifacts/vn`. Tại thư mục `quorum`:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\first-run.ps1
```

Script build 2 container, kiểm tra mô hình, nạp dữ liệu thật rồi báo mở http://localhost:3000. Hướng dẫn đầy đủ và cách
xử lý lỗi: [docs/DOCKER.md](docs/DOCKER.md). Phần dưới đây là cách chạy không dùng Docker.

## Cài đặt trên Windows (không dùng Docker)

Cần **Python 3.11+**, **Node.js 20+** và **Git**. Mở PowerShell tại thư mục `quorum`.

### 1. Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1          # Git Bash: source .venv/Scripts/activate
pip install -r requirements.txt
cd ..
copy .env.example .env                 # rồi mở .env, điền GEMINI_API_KEY
```

PyTorch bản mặc định trên Windows đã chạy được bằng CPU; mô hình rất nhẹ (khoảng 0,15 giây cho một ngày dự đoán).

### 2. Artifacts của mô hình

Chép thư mục `artifacts/vn` (từ file `midmoe_vn_artifacts.zip` của notebook `midmoe-vn-transfer-weights`) vào
`quorum/artifacts/vn`. Kiểm tra mô hình chạy khớp Kaggle:

```powershell
cd backend
python -m pytest
```

Test `test_parity_with_kaggle_reference` phải qua: nghĩa là bản đóng gói cho ra đúng điểm số như notebook.

### 3. Nạp dữ liệu

Chạy trong thư mục `backend` (đã kích hoạt `.venv`):

```powershell
python -m app.cli init                         # tạo cơ sở dữ liệu + 78 mã
python -m app.cli seed-history                 # 243 phiên kiểm định 2025 từ test cube (~1 phút)
python -m app.cli prices                       # giá 78 mã + VN-Index từ 01/2024 đến nay (~2 phút)
python -m app.cli news --from 2026-10-01       # tin CafeF + nhúng PhoBERT (lần đầu tải ~540 MB model)
python -m app.cli backfill --from 2026-01-02   # chạy mô hình cho từng phiên từ đầu năm 2026
```

Sau đó mỗi ngày chỉ cần `python -m app.cli daily`, hoặc để lịch tự chạy (bước 5).

Không có mạng hoặc chỉ muốn xem giao diện: `python -m app.cli demo` nạp giá **giả lập** và chạy mô hình trên đó.
Giao diện sẽ hiện nhãn "Giá giả lập". Đừng dùng lệnh này trên cơ sở dữ liệu dùng để demo thật; muốn làm lại từ đầu thì
xoá file `data/quorum.db`.

### 4. Chạy ứng dụng

Terminal 1, backend:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000
```

Terminal 2, frontend:

```powershell
cd frontend
npm install
copy .env.local.example .env.local
npm run dev
```

Mở http://localhost:3000. Tài liệu API tự sinh: http://localhost:8000/docs.

### 5. Lịch chạy hằng ngày

Chọn một trong hai cách:

* Đặt `RUN_SCHEDULER=true` trong `.env`: mỗi lần khởi động API tự bù dữ liệu và dự báo cho các phiên còn thiếu, sau đó chạy job 16:30 (thứ 2 đến thứ 6) và cập nhật giá 5 phút một lần trong phiên. Bản Docker đã bật sẵn.
* Hoặc mở terminal riêng: `python -m app.cli scheduler`.

## Các trang

| Đường dẫn | Nội dung |
| --- | --- |
| `/` | Gợi ý cho phiên tới, VN-Index, độ rộng, bản đồ thị trường, mã tăng/giảm, tăng hạng mạnh |
| `/bang-gia` | Bảng giá 78 mã theo ngành, màu theo quy ước trần/sàn/tham chiếu, cột hạng AI |
| `/goi-y` | Xếp hạng đủ 78 mã, xem lại các ngày trước cùng kết quả thực tế phiên sau |
| `/co-phieu/[mã]` | Biểu đồ nến + hạng AI, lý do xếp hạng, 7 chỉ báo, tin tức, cùng ngành, lịch sử gợi ý |
| `/bo-loc` | Lọc theo ngành, hạng AI, số mô hình đồng thuận, RSI, % thay đổi, thanh khoản |
| `/theo-doi` | Danh sách theo dõi (cần đăng nhập) |
| `/hieu-qua` | Lợi nhuận cộng dồn top-K so với cả rổ và VN-Index, nhật ký từng phiên |
| `/gioi-thieu` | Cách Quorum hoạt động và hạn chế |

## Ghi chú về mô hình và dữ liệu

* **Tiền xử lý khớp lúc train.** Giá chia 1000 (nghìn đồng) như vnstock; RSI/MACD viết lại theo đúng quy ước
  pandas-ta 0.4.x (notebook in ra 1 giá trị thiếu cho RSI, 25 cho MACD, test kiểm tra điều này); chuẩn hoá bằng đúng
  `vn_norm_params.json`; mỗi mã lấy một tin CafeF mới nhất trong 5 ngày, nhúng bằng `vinai/phobert-base`, trung bình mọi
  token với độ dài 64.
* **Ensemble.** Thứ hạng cuối là trung bình thứ hạng của 10 seed; "đồng thuận" là số seed xếp mã vào top 5.
* **Hiệu quả thật.** Trên dữ liệu kiểm định 2025, từng seed riêng lẻ đạt Sharpe theo phiên trung bình 0,041 như trong
  bài báo, nhưng bản gộp 10 seed chỉ khoảng 0,03 và chưa vượt chọn ngẫu nhiên một cách có ý nghĩa thống kê. Trang
  `/hieu-qua` hiển thị đúng số liệu này.
* **vnstock và pandas-ta** đều không còn trên PyPI, nên dự án gọi thẳng endpoint KBS và tự cài đặt RSI/MACD.

## Kiểm thử

```powershell
cd backend; python -m pytest       # 18 test: chỉ báo, ensemble, parity với Kaggle, parser nguồn dữ liệu, API, trợ lý
cd frontend; npm run build         # kiểm tra kiểu TypeScript và build production
```

## Quy trình git

Xem [docs/GIT_WORKFLOW.md](docs/GIT_WORKFLOW.md): cách tạo repo, issue, nhánh, commit và pull request, cùng script
`scripts/publish_history.py` đưa toàn bộ code lên GitHub theo từng tính năng.
