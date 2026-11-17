"""Đưa toàn bộ code Quorum lên GitHub theo quy trình issue → nhánh → commit → pull request → merge.

Chạy một lần rồi để máy tự làm (khoảng 10-15 phút):

    python scripts/publish_history.py --repo quorum

Yêu cầu: git và GitHub CLI (gh) đã cài, đã chạy `gh auth login`. Chi tiết: docs/GIT_WORKFLOW.md.

Script ghi tiến độ vào .git/publish_state.json, nên nếu bị ngắt giữa chừng chỉ cần chạy lại
đúng lệnh cũ: các bước đã xong sẽ được bỏ qua.

Commit message chỉ gồm đúng nội dung ghi trong PLAN bên dưới, không có dòng Co-authored-by.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / ".git" / "publish_state.json"

B = "backend/"
F = "frontend/"
LABELS = {
    "setup": ("ededed", "Cấu hình dự án"),
    "ml": ("0b5563", "Mô hình MIDMoE"),
    "data": ("1f7ae0", "Dữ liệu và pipeline"),
    "backend": ("5319e7", "API backend"),
    "assistant": ("8e3cc7", "Trợ lý AI"),
    "frontend": ("0a8a44", "Giao diện web"),
    "docs": ("b07d00", "Tài liệu"),
}

# Mỗi phần tử là một issue + một pull request. "commits" là danh sách (message, [đường dẫn]).
PLAN = [
    {
        "slug": "project-setup", "labels": ["setup"], "branch": "chore/project-setup",
        "title": "Thiết lập khung dự án Quorum",
        "body": "Tạo file cấu hình môi trường, danh sách thư viện backend và hướng dẫn đặt artifacts của mô hình.",
        "commits": [
            ("chore: add environment template and backend requirements", [".env.example", B + "requirements.txt", B + "pytest.ini"]),
            ("docs: describe the model artifacts layout", ["artifacts/README.md"]),
        ],
    },
    {
        "slug": "model-package", "labels": ["ml"],
        "title": "Đóng gói mô hình MIDMoE để chạy dự đoán",
        "body": (
            "Chép kiến trúc MarketMoE từ notebook Kaggle, nạp 10 bộ trọng số và gộp thành ensemble.\n\n"
            "- [ ] Kết quả khớp tuyệt đối với `vn_parity_ref.npz`\n"
            "- [ ] 7 chỉ báo tính giống pandas-ta 0.4.x mà notebook đã dùng\n"
            "- [ ] Dựng cube 16 phiên cho một ngày\n"
            "- [ ] Nhúng tin bằng PhoBERT, chọn tin mới nhất trong 5 ngày\n"
            "- [ ] Giải thích bằng cách tắt từng nguồn thông tin"
        ),
        "commits": [
            ("feat(ml): port the MarketMoE architecture from the Kaggle notebook",
             [B + "app/__init__.py", B + "app/ml/__init__.py", B + "app/ml/marketmoe.py"]),
            ("feat(ml): load exported artifacts and run the 10-seed ensemble", [B + "app/ml/artifacts.py", B + "app/ml/predictor.py"]),
            ("feat(ml): technical indicators and normalisation", [B + "app/ml/features.py"]),
            ("feat(ml): build the one-day input cube", [B + "app/ml/cube.py"]),
            ("feat(ml): PhoBERT title embeddings and news selection", [B + "app/ml/news.py"]),
            ("feat(ml): explain rankings by switching off each information source", [B + "app/ml/explain.py"]),
            ("test(ml): indicators, ensemble and parity with the notebook",
             [B + "tests/__init__.py", B + "tests/conftest.py", B + "tests/test_model.py"]),
        ],
    },
    {
        "slug": "data-layer", "labels": ["data", "backend"],
        "title": "Cơ sở dữ liệu và nguồn dữ liệu giá, tin tức",
        "body": "Cấu hình, bảng dữ liệu (SQLAlchemy), nguồn giá KBS và crawler tin CafeF theo đúng cách notebook đã thu thập.",
        "commits": [
            ("feat(db): settings, database session and models",
             [B + "app/config.py", B + "app/db.py", B + "app/models.py", B + "app/reference.py"]),
            ("feat(data): daily prices from KBS", [B + "app/sources/__init__.py", B + "app/sources/kbs.py"]),
            ("feat(data): CafeF news crawler", [B + "app/sources/cafef.py"]),
            ("test(data): price and news parsers", [B + "tests/test_sources.py"]),
        ],
    },
    {
        "slug": "daily-pipeline", "labels": ["data", "ml"],
        "title": "Pipeline cập nhật dữ liệu và chạy mô hình hằng ngày",
        "body": (
            "16:30 mỗi ngày giao dịch: tải giá, tin tức, chạy mô hình, lưu gợi ý và giải thích, cập nhật lợi suất thực tế.\n"
            "Kèm lệnh nạp lịch sử kiểm định 2025 từ test cube và dữ liệu giả lập để phát triển giao diện."
        ),
        "commits": [
            ("feat(pipeline): storage helpers", [B + "app/pipeline/__init__.py", B + "app/pipeline/store.py"]),
            ("feat(pipeline): daily job, backfill and realised returns", [B + "app/pipeline/jobs.py"]),
            ("feat(pipeline): seed the 2025 out-of-sample history", [B + "app/pipeline/history.py"]),
            ("feat(pipeline): synthetic prices for offline development", [B + "app/pipeline/demo.py"]),
            ("feat(pipeline): scheduler and command line interface", [B + "app/pipeline/scheduler.py", B + "app/cli.py"]),
        ],
    },
    {
        "slug": "rest-api", "labels": ["backend"],
        "title": "REST API cho bảng giá, gợi ý AI, chi tiết mã và tài khoản",
        "body": "Service layer dùng chung cho API và trợ lý; đăng ký, đăng nhập bằng JWT; danh sách theo dõi.",
        "commits": [
            ("feat(api): service layer for market, picks, stocks and performance", [B + "app/services/"]),
            ("feat(api): password hashing and JWT authentication", [B + "app/auth.py"]),
            ("feat(api): REST endpoints", [B + "app/api.py"]),
        ],
    },
    {
        "slug": "ai-assistant", "labels": ["assistant", "backend"],
        "title": "Trợ lý AI dùng Gemini, trả lời bằng dữ liệu của hệ thống",
        "body": (
            "Gemini gọi các công cụ tra cứu (function calling) thay vì tự đoán số liệu; trả lời dạng stream (SSE).\n\n"
            "- [ ] Không khuyên mua bán, không dự đoán giá\n- [ ] Hiểu ngữ cảnh trang đang xem"
        ),
        "commits": [
            ("feat(assistant): data tools and system prompt",
             [B + "app/assistant/__init__.py", B + "app/assistant/tools.py", B + "app/assistant/prompts.py"]),
            ("feat(assistant): Gemini tool-calling loop", [B + "app/assistant/agent.py"]),
            ("feat(api): streaming chat endpoint and application entry point", [B + "app/chat.py", B + "app/main.py"]),
            ("test: API endpoints and assistant loop", [B + "tests/test_api.py", B + "tests/test_assistant.py"]),
        ],
    },
    {
        "slug": "brand", "labels": ["frontend"],
        "title": "Nhận diện thương hiệu Quorum",
        "body": "Logo: khung vuông có đuôi tạo thành chữ Q, bên trong ba cột tăng dần thể hiện thứ hạng.",
        "commits": [("feat(brand): Quorum logo mark and app icon", ["docs/brand/"])],
    },
    {
        "slug": "web-foundation", "labels": ["frontend"],
        "title": "Nền tảng giao diện web: Next.js, design tokens, thành phần dùng chung",
        "body": "Bảng màu theo quy ước bảng giá Việt Nam, font Be Vietnam Pro, bảng dữ liệu dày, góc vuông, không đổ bóng.",
        "commits": [
            ("chore(web): Next.js, TypeScript and Tailwind setup",
             [F + "package.json", F + "package-lock.json", F + "next.config.mjs", F + "postcss.config.mjs",
              F + "tailwind.config.ts", F + "tsconfig.json", F + ".gitignore", F + ".env.local.example"]),
            ("feat(web): design tokens and global styles", [F + "src/app/globals.css", F + "src/app/icon.svg"]),
            ("feat(web): API client, number formatting and session context", [F + "src/lib/"]),
            ("feat(web): logo, quorum strip and shared UI pieces", [F + "src/components/ui/"]),
            ("feat(web): top bar, ticker search and market strip", [F + "src/components/shell/"]),
            ("feat(web): candlestick, line and market-map charts", [F + "src/components/charts/"]),
        ],
    },
    {
        "slug": "web-assistant", "labels": ["frontend", "assistant"],
        "title": "Sidebar trợ lý AI trên web",
        "body": "Panel chat bên phải, nhận câu trả lời dạng stream, gợi ý câu hỏi theo trang, thẻ mã bấm được.",
        "commits": [
            ("feat(web): assistant side panel with streaming answers", [F + "src/components/chat/"]),
            ("feat(web): root layout and not-found page", [F + "src/app/layout.tsx", F + "src/app/not-found.tsx"]),
        ],
    },
    {
        "slug": "web-market", "labels": ["frontend"],
        "title": "Trang tổng quan và bảng giá",
        "body": "Gợi ý cho phiên tới, VN-Index, độ rộng thị trường, bản đồ thị trường; bảng giá 78 mã theo ngành.",
        "commits": [
            ("feat(web): market overview page", [F + "src/app/page.tsx"]),
            ("feat(web): price board", [F + "src/app/bang-gia/"]),
        ],
    },
    {
        "slug": "web-picks", "labels": ["frontend"],
        "title": "Trang gợi ý AI và chi tiết cổ phiếu",
        "body": "Bảng xếp hạng 78 mã có lịch sử; trang mã với biểu đồ nến, hạng AI, lý do xếp hạng, chỉ báo, tin tức.",
        "commits": [
            ("feat(web): AI picks ranking page", [F + "src/app/goi-y/"]),
            ("feat(web): stock detail page with explanation", [F + "src/app/co-phieu/"]),
        ],
    },
    {
        "slug": "web-account", "labels": ["frontend"],
        "title": "Bộ lọc cổ phiếu, danh sách theo dõi và tài khoản",
        "body": "Lọc theo ngành, hạng AI, số phiếu, RSI, thanh khoản; đăng ký, đăng nhập; gắn sao theo dõi mã.",
        "commits": [
            ("feat(web): stock screener", [F + "src/app/bo-loc/"]),
            ("feat(web): sign in and sign up", [F + "src/components/auth-form.tsx", F + "src/app/dang-nhap/", F + "src/app/dang-ky/"]),
            ("feat(web): watchlist page", [F + "src/app/theo-doi/"]),
        ],
    },
    {
        "slug": "web-performance", "labels": ["frontend"],
        "title": "Trang hiệu quả gợi ý và giới thiệu cách hoạt động",
        "body": "So sánh top-K với cả rổ và VN-Index, nhật ký từng phiên; trang giải thích cách Quorum hoạt động.",
        "commits": [
            ("feat(web): track record page", [F + "src/app/hieu-qua/"]),
            ("feat(web): how Quorum works page", [F + "src/app/gioi-thieu/"]),
        ],
    },
    {
        "slug": "docker", "labels": ["setup"],
        "title": "Đóng gói và chạy bằng Docker",
        "body": "Image cho API (PyTorch CPU) và web (Next.js standalone), docker-compose, script chạy lần đầu trên Windows.",
        "commits": [
            ("build: Dockerfile for the API", [B + "Dockerfile", ".dockerignore"]),
            ("build: standalone Next.js image", [F + "Dockerfile", F + ".dockerignore", F + "next.config.mjs"]),
            ("build: docker compose stack and first-run script", ["docker-compose.yml", "scripts/first-run.ps1"]),
        ],
    },
    {
        "slug": "docs", "labels": ["docs"], "branch": "docs/guides",
        "title": "Tài liệu cài đặt, vận hành và quy trình git",
        "body": "README hướng dẫn chạy trên Windows, các lệnh pipeline, và quy trình làm việc với issue/PR.",
        "commits": [
            ("docs: setup and operations guide", ["README.md"]),
            ("docs: running Quorum with Docker", ["docs/DOCKER.md"]),
            ("docs: git workflow and history publishing script", ["docs/GIT_WORKFLOW.md", "scripts/publish_history.py"]),
        ],
    },
]

INIT_FILES = [".gitignore", ".gitattributes", ".editorconfig"]


def run(cmd: list[str], check: bool = True, capture: bool = True) -> str:
    print("  $", " ".join(cmd))
    r = subprocess.run(cmd, cwd=ROOT, text=True, encoding="utf-8", capture_output=capture)
    if check and r.returncode != 0:
        print(r.stdout or "", r.stderr or "", file=sys.stderr)
        raise SystemExit(f"Lệnh thất bại: {' '.join(cmd)}")
    return (r.stdout or "").strip()


def load_state() -> dict:
    return json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {"done": []}


def save_state(st: dict) -> None:
    STATE.write_text(json.dumps(st, indent=2, ensure_ascii=False), encoding="utf-8")


def commit(message: str, paths: list[str]) -> None:
    missing = [p for p in paths if not (ROOT / p).exists()]
    if missing:
        raise SystemExit(f"Không tìm thấy: {missing}")
    run(["git", "add", "--", *paths])
    if not run(["git", "diff", "--cached", "--name-only"]):
        print("  (không có thay đổi, bỏ qua commit)")
        return
    assert "co-authored-by" not in message.lower()
    # --no-verify: tránh hook tự thêm trailer; -c commit.template= bỏ template nếu có
    run(["git", "-c", "commit.template=", "commit", "--no-verify", "-m", message])


def preflight(args) -> None:
    for tool in ("git", "gh"):
        if not shutil.which(tool):
            raise SystemExit(f"Chưa cài {tool}. Xem docs/GIT_WORKFLOW.md")
    if subprocess.run(["gh", "auth", "status"], cwd=ROOT, capture_output=True).returncode != 0:
        raise SystemExit("Chưa đăng nhập GitHub CLI. Chạy: gh auth login")
    if not run(["git", "config", "user.name"], check=False) or not run(["git", "config", "user.email"], check=False):
        raise SystemExit('Chưa cấu hình tên/email git. Chạy: git config --global user.name "Tên" và user.email "email"')
    for item in PLAN:
        for _, paths in item["commits"]:
            for p in paths:
                if not (ROOT / p).exists():
                    raise SystemExit(f"Thiếu file trong kế hoạch: {p}")
    if (ROOT / "artifacts" / "vn").exists():
        ignored = run(["git", "check-ignore", "artifacts/vn"], check=False) if (ROOT / ".git").exists() else "artifacts/vn"
        if not ignored and (ROOT / ".git").exists():
            raise SystemExit("artifacts/vn không bị .gitignore bỏ qua: dừng để tránh đẩy trọng số lên GitHub")


def ensure_repo(args, st: dict) -> None:
    if "init" in st["done"]:
        return
    if not (ROOT / ".git").exists():
        run(["git", "init", "-b", "main"])
    has_commit = subprocess.run(["git", "rev-parse", "--verify", "HEAD"], cwd=ROOT, capture_output=True).returncode == 0
    if not has_commit:  # `git init` cũ có thể tạo nhánh master: đổi sang main trước commit đầu
        run(["git", "symbolic-ref", "HEAD", "refs/heads/main"])
    elif run(["git", "branch", "--show-current"]) != "main":
        run(["git", "branch", "-M", "main"])
    tracked = run(["git", "ls-files"], check=False).splitlines()
    extra = [f for f in tracked if f not in INIT_FILES]
    if extra:
        raise SystemExit(
            f"Repo đã có {len(extra)} file được commit (ví dụ {extra[0]}). Script cần repo chưa commit gì để tự chia commit.\n"
            "Xoá thư mục .git rồi chỉ chạy: git init, git remote add origin <link>, sau đó chạy lại script."
        )
    if run(["git", "remote"], check=False) and run(["git", "ls-remote", "--heads", "origin", "main"], check=False):
        local = run(["git", "rev-parse", "HEAD"], check=False) if has_commit else ""
        remote = run(["git", "ls-remote", "origin", "refs/heads/main"]).split()[0]
        if remote != local:
            raise SystemExit(
                "Repo trên GitHub đã có commit (thường do tick 'Add a README' khi tạo repo).\n"
                "Xoá repo đó, tạo lại repo TRỐNG (không README, không .gitignore, không license) rồi chạy lại."
            )
    commit("chore: initialize repository", INIT_FILES)
    if not run(["git", "remote"], check=False):
        visibility = "--public" if args.public else "--private"
        name = f"{args.owner}/{args.repo}" if args.owner else args.repo
        run(["gh", "repo", "create", name, visibility, "--source", ".", "--remote", "origin",
             "--description", "Quorum: gợi ý cổ phiếu Việt Nam bằng mô hình học sâu MIDMoE và trợ lý AI"])
    run(["git", "push", "-u", "origin", "main"])
    for name, (color, desc) in LABELS.items():
        run(["gh", "label", "create", name, "--color", color, "--description", desc, "--force"], check=False)
    st["done"].append("init")
    save_state(st)


def publish_item(item: dict, st: dict, delay: float) -> None:
    key = item["slug"]
    if key in st["done"]:
        print(f"Bỏ qua (đã xong): {item['title']}")
        return
    print(f"\n=== {item['title']}")
    run(["git", "checkout", "main"])
    run(["git", "pull", "--ff-only", "origin", "main"])
    issue_no = st.get("issues", {}).get(key)
    if not issue_no:
        url = run(["gh", "issue", "create", "--title", item["title"], "--body", item["body"],
                   *sum((["--label", lb] for lb in item["labels"]), [])])
        issue_no = int(re.search(r"/issues/(\d+)", url).group(1))
        st.setdefault("issues", {})[key] = issue_no
        save_state(st)
    branch = item.get("branch", f"feat/{key}")
    existing = run(["git", "branch", "--list", branch])
    run(["git", "checkout", branch] if existing else ["git", "checkout", "-b", branch])
    for message, paths in item["commits"]:
        commit(message, paths)
        time.sleep(delay)
    run(["git", "push", "-u", "origin", branch])
    lines = "\n".join(f"- {m}" for m, _ in item["commits"])
    pr_body = f"{item['body']}\n\n### Thay đổi\n{lines}\n\nCloses #{issue_no}"
    pr_url = run(["gh", "pr", "create", "--base", "main", "--head", branch, "--title", item["title"], "--body", pr_body,
                  *sum((["--label", lb] for lb in item["labels"]), [])], check=False)
    if "pull" not in pr_url:
        pr_url = run(["gh", "pr", "view", branch, "--json", "url", "-q", ".url"])
    time.sleep(delay)
    run(["gh", "pr", "merge", pr_url, "--merge", "--delete-branch"])
    run(["git", "checkout", "main"])
    run(["git", "pull", "--ff-only", "origin", "main"])
    run(["git", "branch", "-D", branch], check=False)
    st["done"].append(key)
    save_state(st)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--repo", default="quorum", help="tên repo GitHub sẽ tạo (mặc định: quorum)")
    p.add_argument("--owner", default="", help="tài khoản hoặc tổ chức sở hữu repo (mặc định: tài khoản đang đăng nhập gh)")
    p.add_argument("--public", action="store_true", help="tạo repo công khai (mặc định: riêng tư)")
    p.add_argument("--delay", type=float, default=3.0, help="số giây nghỉ giữa các bước gọi GitHub")
    p.add_argument("--dry-run", action="store_true", help="chỉ in kế hoạch, không chạy lệnh nào")
    args = p.parse_args()

    if args.dry_run:
        for i, item in enumerate(PLAN, 1):
            print(f"{i:2d}. [{', '.join(item['labels'])}] {item['title']}")
            for m, paths in item["commits"]:
                print(f"      - {m}  ({len(paths)} đường dẫn)")
        return

    preflight(args)
    st = load_state() if (ROOT / ".git").exists() else {"done": []}
    ensure_repo(args, st)
    for item in PLAN:
        publish_item(item, st, args.delay)
    leftover = run(["git", "status", "--porcelain"])
    print("\nXong. Repo:", run(["gh", "repo", "view", "--json", "url", "-q", ".url"], check=False))
    if leftover:
        print("Còn file chưa nằm trong commit nào (kiểm tra lại):\n" + leftover)


if __name__ == "__main__":
    main()
