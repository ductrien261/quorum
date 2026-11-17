<div align="center">

<img src="docs/brand/logo-app-icon.svg" alt="Logo Quorum" width="96" />

# Quorum

**Hệ thống khuyến nghị đầu tư chứng khoán thông minh dựa trên mô hình học sâu phân cấp và trợ lý ảo AI**

![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)
![PyTorch](https://img.shields.io/badge/PyTorch-CPU-EE4C2C?logo=pytorch&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-15-000000?logo=nextdotjs&logoColor=white)
![Gemini](https://img.shields.io/badge/Gemini-function%20calling-4285F4?logo=googlegemini&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-compose-2496ED?logo=docker&logoColor=white)

[Giới thiệu](#giới-thiệu) ·
[Demo](#demo) ·
[Kiến trúc](#kiến-trúc) ·
[Bắt đầu nhanh](#bắt-đầu-nhanh) ·
[Cấu hình](#cấu-hình) ·
[Trang và API chính](#trang-và-api-chính) ·
[Tài liệu](#tài-liệu)

</div>

---

## Giới thiệu

Nhà đầu tư cá nhân thường phải tự đọc bảng giá, chỉ báo kỹ thuật và tin tức của hàng chục mã mỗi ngày. Các công cụ
"gợi ý mã" có sẵn hầu như không nói rõ vì sao một mã được chọn.

Quorum là một ứng dụng web chạy trên dữ liệu thị trường Việt Nam. Mỗi chiều sau phiên giao dịch, hệ thống tự lấy giá
và tin tức, chạy mô hình học sâu để xếp hạng **78 cổ phiếu** cho phiên kế tiếp và giải thích vì sao mỗi mã có thứ hạng đó.

Ứng dụng gồm hai phần:

1. **Sản phẩm cho người dùng:** bảng giá, bản đồ nhiệt, gợi ý theo ngày, trang chi tiết mã với biểu đồ và chỉ báo, bộ
   lọc, danh sách theo dõi và trang đo hiệu quả gợi ý một cách minh bạch.
2. **Trợ lý AI:** Gemini được nối với cơ sở dữ liệu qua function calling. Nó trả lời bằng tiếng Việt từ kết quả thật của
   mô hình, không trả lời theo trí nhớ của mô hình ngôn ngữ.

> Điểm AI là công cụ tham khảo, không phải khuyến nghị đầu tư.

### Ai dùng và dùng để làm gì

| Người dùng | Dùng Quorum để |
| --- | --- |
| Khách chưa đăng nhập | Xem bảng giá, gợi ý phiên tới, chi tiết mã, bộ lọc, hiệu quả gợi ý và hỏi trợ lý |
| Thành viên đã đăng nhập | Thêm vào đó: lưu danh sách theo dõi, trợ lý trả lời theo danh sách của mình |
| Người vận hành | Chạy pipeline, nạp lịch sử, theo dõi log job và trạng thái dữ liệu qua `/api/health` |

### Tính năng nổi bật

**Thị trường**
- Bảng giá 78 mã theo quy ước màu của sàn Việt Nam (trần tím, sàn xanh lam, tham chiếu vàng), kèm cột biên độ trong phiên
  và biểu đồ mini 30 phiên.
- Độ rộng thị trường, mã biến động mạnh nhất, dòng tiền theo ngành.
- Bản đồ nhiệt: diện tích theo giá trị giao dịch, màu theo % thay đổi.

**Gợi ý từ mô hình**
- Xếp hạng đủ 78 mã cho phiên kế tiếp, độ đồng thuận giữa các mô hình, mức tăng giảm hạng so với hôm trước.
- Xem lại gợi ý của các ngày trước cùng lợi nhuận thực tế của phiên sau đó.
- Lý do xếp hạng: lần lượt bỏ từng nguồn thông tin (thị trường chung, diễn biến giá, tin tức, ngành) để xem hạng thay
  đổi ra sao, kèm 7 chỉ báo kỹ thuật và tin CafeF được mô hình sử dụng.

**Phân tích kỹ thuật**
- Biểu đồ nến với menu chỉ báo: MA20, MA50, MA200, dải Bollinger, hồi quy tuyến tính (đường xu hướng, kênh ±2σ, độ dốc và
  R²), RSI, MACD và hạng AI theo thời gian.
- Bộ lọc theo ngành, hạng AI, độ đồng thuận, RSI, % thay đổi và thanh khoản.

**Trợ lý AI**
- Biết người dùng đang xem trang nào hoặc mã nào. Trả lời dạng stream và hiện bước đang tra cứu.
- 11 công cụ đọc dữ liệu: gợi ý, chi tiết mã, lịch sử giá, lịch sử hạng, tin tức, so sánh, lọc, tổng quan thị trường,
  hiệu quả gợi ý, thông tin mô hình, danh sách theo dõi.

**Vận hành**
- Lịch tự chạy: cập nhật giá 5 phút một lần trong phiên và chạy mô hình lúc 16:30 từ thứ 2 đến thứ 6.
- Mỗi lần khởi động, hệ thống tự bù những phiên còn thiếu khi máy tắt.
- Một lệnh Docker để chạy cả hệ thống.

## Demo

<div align="center">

![Quorum demo](docs/media/quorum-demo.gif)

</div>

## Kiến trúc

```mermaid
flowchart LR
    subgraph Nguon["Nguồn dữ liệu"]
        KBS["KBS<br/>giá ngày 78 mã + VN-Index"]
        CafeF["CafeF<br/>tin tức theo mã"]
    end

    subgraph Backend["Backend (FastAPI)"]
        Sched["Lịch chạy<br/>APScheduler"]
        Pipe["Pipeline<br/>chỉ báo · cube · PhoBERT"]
        Model["Mô hình<br/>xếp hạng"]
        DB[("SQLite / PostgreSQL")]
        API["REST API"]
        Agent["Trợ lý<br/>11 công cụ"]
    end

    Web["Next.js<br/>localhost:3000"]
    Gemini["Gemini API"]
    Art["artifacts/vn<br/>trọng số mô hình"]

    KBS --> Pipe
    CafeF --> Pipe
    Sched --> Pipe
    Art --> Model
    Pipe --> Model --> DB
    DB --> API --> Web
    Web -- "câu hỏi" --> Agent
    Agent <--> Gemini
    Agent --> DB
```

### Trợ lý trả lời một câu hỏi như thế nào

```mermaid
sequenceDiagram
    autonumber
    actor U as Người dùng
    participant W as Web
    participant A as API /chat
    participant G as Gemini
    participant D as Cơ sở dữ liệu

    U->>W: "Vì sao VCB được xếp hạng như vậy?"
    W->>A: câu hỏi + ngữ cảnh (đang xem VCB)
    A->>G: system prompt + danh sách công cụ
    G-->>A: gọi get_stock("VCB")
    A->>D: hạng, phiếu, ablation, chỉ báo, tin
    D-->>A: JSON
    A->>G: kết quả công cụ
    G-->>A: câu trả lời (stream)
    A-->>W: từng đoạn văn bản
    W-->>U: hiển thị dần + liên kết mã
```

### Một ngày của pipeline

```mermaid
stateDiagram-v2
    [*] --> TrongPhien: 9:00
    TrongPhien --> TrongPhien: cập nhật giá 5 phút/lần
    TrongPhien --> DongCua: 15:05
    DongCua --> ChayMoHinh: 16:30
    ChayMoHinh --> CoGoiY: lưu hạng, phiếu, giải thích
    CoGoiY --> [*]: điền lợi nhuận thực tế của phiên trước
```

### Bảo mật

| Vấn đề | Cách xử lý |
| --- | --- |
| Mật khẩu | Băm bằng bcrypt, không lưu bản rõ |
| Đăng nhập | JWT ký bằng `JWT_SECRET`, hết hạn sau 7 ngày |
| Key Gemini | Chỉ nằm ở backend trong `.env`, trình duyệt không thấy |
| Lạm dụng trợ lý | Giới hạn số câu hỏi mỗi giờ, giới hạn số vòng gọi công cụ |
| Dữ liệu không đưa lên git | `.env`, `data/`, `artifacts/vn/` nằm trong `.gitignore` |

## Bắt đầu nhanh

### Yêu cầu

- Docker Desktop (cách khuyên dùng), **hoặc** Python 3.11+ và Node.js 20+
- Key Gemini lấy tại https://aistudio.google.com/apikey
- Thư mục `artifacts/vn` chứa trọng số mô hình (xem [artifacts/README.md](artifacts/README.md))

### Chạy bằng Docker

```powershell
git clone https://github.com/<tai-khoan>/quorum.git
cd quorum
copy .env.example .env          # điền GEMINI_API_KEY
# chép artifacts/vn vào đúng chỗ
powershell -ExecutionPolicy Bypass -File scripts\first-run.ps1
```

Lần đầu mất khoảng 15 đến 40 phút (tải PyTorch, PhoBERT, giá và tin). Xong thì mở http://localhost:3000.
Từ lần sau chỉ cần:

```powershell
docker compose up -d
```

Hướng dẫn đầy đủ và cách xử lý lỗi: [docs/DOCKER.md](docs/DOCKER.md).

### Chạy ở chế độ phát triển

```powershell
# Backend
cd backend
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m app.cli init
python -m app.cli seed-history
python -m app.cli prices
python -m app.cli backfill --from 2026-01-02
uvicorn app.main:app --reload --port 8000

# Frontend (terminal khác)
cd frontend
npm install
copy .env.local.example .env.local
npm run dev
```

Không có mạng thì chạy `python -m app.cli demo` để có dữ liệu giả lập. Giao diện sẽ hiện nhãn "Giá giả lập".

### Lệnh thường dùng

| Lệnh | Việc |
| --- | --- |
| `docker compose up -d` / `down` | Bật / tắt cả hệ thống |
| `docker compose up -d --build` | Build lại sau khi sửa code |
| `docker compose logs -f api` | Xem log backend |
| `python -m app.cli catch-up` | Bù giá, tin và dự báo cho mọi phiên còn thiếu |
| `python -m app.cli daily` | Chạy job 16:30 ngay |
| `python -m app.cli backfill --from 2026-11-01` | Chạy lại mô hình cho một khoảng ngày |
| `python -m app.cli news --from 2026-11-01` | Tải thêm tin và nhúng PhoBERT |
| `python -m app.cli demo` | Nạp dữ liệu giả lập để xem giao diện |

Với Docker, thêm `docker compose exec api` trước các lệnh `python -m app.cli`.

## Cấu hình

Các biến trong file `.env` ở thư mục gốc:

| Biến | Ý nghĩa | Mặc định |
| --- | --- | --- |
| `GEMINI_API_KEY` | Key cho trợ lý AI | (trống, trợ lý tắt) |
| `GEMINI_MODEL` | Tên model Gemini | `gemini-3.5-flash` |
| `DATABASE_URL` | Chuỗi kết nối cơ sở dữ liệu | SQLite tại `data/quorum.db` |
| `ARTIFACT_DIR` | Thư mục trọng số mô hình | `artifacts/vn` |
| `JWT_SECRET` | Chuỗi bí mật ký token đăng nhập | cần đổi trước khi dùng |
| `CORS_ORIGINS` | Địa chỉ frontend được gọi API | `http://localhost:3000` |
| `RUN_SCHEDULER` | Chạy lịch tự động trong tiến trình API | `false` (Docker: `true`) |
| `PRICE_HISTORY_START` | Ngày bắt đầu tải lịch sử giá | `2024-01-01` |
| `NEWS_ENABLED` | Lấy tin CafeF và nhúng PhoBERT | `true` |
| `CHAT_RATE_LIMIT_PER_HOUR` | Số câu hỏi tối đa mỗi giờ | `60` |

Muốn dùng PostgreSQL:

```env
DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/quorum
```

## Trang và API chính

| Trang | Nội dung |
| --- | --- |
| `/` | Tổng quan: gợi ý phiên tới, VN-Index, độ rộng, bản đồ thị trường |
| `/bang-gia` | Bảng giá, biên độ ngày, biểu đồ 30 phiên, bản đồ nhiệt |
| `/goi-y` | Xếp hạng 78 mã, xem lại các ngày trước và kết quả thực tế |
| `/co-phieu/[mã]` | Biểu đồ nến và chỉ báo, lý do xếp hạng, tin tức, cùng ngành |
| `/bo-loc` | Lọc cổ phiếu theo nhiều tiêu chí |
| `/theo-doi` | Danh sách theo dõi (cần đăng nhập) |
| `/hieu-qua` | Lợi nhuận cộng dồn top-K so với cả rổ và VN-Index |
| `/gioi-thieu` | Cách Quorum hoạt động và hạn chế |
| `/dang-nhap`, `/dang-ky` | Tài khoản |

| Nhóm API | Endpoint |
| --- | --- |
| Hệ thống | `GET /api/health`, `GET /api/tickers`, `GET /api/search` |
| Thị trường | `GET /api/market/overview`, `GET /api/market/board` |
| Gợi ý | `GET /api/ai/dates`, `/ai/picks`, `/ai/rankings`, `/ai/track-record` |
| Cổ phiếu | `GET /api/stocks/{mã}`, `/prices`, `/rank-history`, `/explanation`, `/news`, `/peers` |
| Bộ lọc | `GET /api/screener` |
| Tài khoản | `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me` |
| Theo dõi | `GET /api/watchlist`, `PUT` / `DELETE /api/watchlist/{mã}` |
| Trợ lý | `POST /api/chat` (Server-Sent Events) |

Tài liệu API tự sinh: http://localhost:8000/docs

## Công nghệ

| Phần | Công nghệ |
| --- | --- |
| Mô hình | PyTorch (CPU), Transformers với `vinai/phobert-base` |
| Backend | FastAPI, SQLAlchemy 2, Pydantic Settings, APScheduler, bcrypt, PyJWT |
| Dữ liệu | KBS (giá ngày), CafeF (tin tức), pandas, BeautifulSoup |
| Trợ lý | Google Gemini qua `google-genai`, function calling, SSE |
| Lưu trữ | SQLite (WAL), có thể đổi sang PostgreSQL |
| Giao diện | Next.js 15, React 19, TypeScript, Tailwind CSS, SWR |
| Biểu đồ | lightweight-charts 5, d3-hierarchy |
| Đóng gói | Docker, docker compose, Next.js standalone |

## Tài liệu

| Tài liệu | Nội dung |
| --- | --- |
| [docs/DOCKER.md](docs/DOCKER.md) | Cài và chạy bằng Docker, xử lý lỗi |
| [docs/GIT_WORKFLOW.md](docs/GIT_WORKFLOW.md) | Quy trình issue, nhánh, commit, pull request |
| [artifacts/README.md](artifacts/README.md) | Cách đặt trọng số mô hình |
| [docs/brand/](docs/brand/) | Logo dạng SVG |

## Cấu trúc thư mục

```text
quorum/
├── backend/
│   ├── app/
│   │   ├── ml/          # mô hình, chỉ báo, nhúng tin tức, giải thích
│   │   ├── sources/     # KBS, CafeF
│   │   ├── pipeline/    # job hằng ngày, chạy bù, lịch, dữ liệu giả lập
│   │   ├── services/    # nghiệp vụ cho API
│   │   ├── assistant/   # công cụ, prompt, vòng gọi Gemini
│   │   ├── api.py, chat.py, main.py, cli.py
│   └── tests/
├── frontend/
│   └── src/
│       ├── app/         # các trang
│       ├── components/  # shell, biểu đồ, chat, ui
│       └── lib/         # API client, định dạng số, chỉ báo
├── artifacts/           # trọng số mô hình (không commit)
├── docs/
├── scripts/             # first-run.ps1, publish_history.py
└── docker-compose.yml
```

## Kiểm thử

```powershell
cd backend
python -m pytest          # chỉ báo, mô hình, parser nguồn dữ liệu, API, trợ lý

cd ..\frontend
npm run build             # kiểm tra kiểu TypeScript và build production
```

Trong Docker: `docker compose exec api python -m pytest`.

## Đóng góp

Mỗi thay đổi đi theo quy trình issue, nhánh `feat/...` hoặc `fix/...`, commit theo Conventional Commits và pull request
có dòng `Closes #số-issue`. Chi tiết trong [docs/GIT_WORKFLOW.md](docs/GIT_WORKFLOW.md).
